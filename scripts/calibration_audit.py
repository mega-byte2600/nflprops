"""Calibration audit: the statistical gate of ADR-0003, on real nflverse data.

Read-only measurement; it changes no model code. For each stat it reports:
  A) the repo's published PIT method, unchanged, for comparison;
  B) a randomized PIT against the CDF of exactly what marginals.rvs samples
     (the zero-inflated mixture), with strictly temporal train/test;
  C) the decision quantity, P(over a book-style line) vs the realized hit rate, with a
     player-clustered bootstrap CI, Brier score, and Brier skill score vs a naive baseline
     (the player's historical hit rate at the same line); then the ADR-0003 gate verdict.

    python scripts/calibration_audit.py cache/player_stats.csv [--test 2022 2023]
        [--td-single-inflation] [--json out.json]

References: Czado, Gneiting & Held (2009) randomized PIT; Gneiting & Raftery (2007)
proper scoring rules; Brier (1950).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

import numpy as np
import pandas as pd
from scipy import stats

from nflprops import data as d
from nflprops import marginals as M
from nflprops.calibration import pit_backtest

STATS = ("passing_yards", "rushing_yards", "receiving_yards", "rushing_tds", "receiving_tds")
DISCRETE = {"rushing_tds", "receiving_tds"}
GATE = {"max_abs_gap": 0.02, "min_players": 50, "min_games": 1000}


def _active_cdf(fit: M.Marginal, y: np.ndarray) -> np.ndarray:
    if fit.family == "gamma_zinf":
        return stats.gamma.cdf(y, fit.params[0], 0, fit.params[1])
    if fit.family == "normal_zinf":
        return stats.norm.cdf(y, *fit.params)
    if fit.family == "poisson":
        return stats.poisson.cdf(np.floor(y), fit.params[0])
    return stats.nbinom.cdf(np.floor(y), *fit.params)


def model_cdf(fit: M.Marginal, y, p_active: float) -> np.ndarray:
    """CDF of what rvs samples: 0 with prob 1 - p_active, else max(V, 0)."""
    y = np.asarray(y, dtype=float)
    return np.where(y < 0, 0.0, (1 - p_active) + p_active * _active_cdf(fit, y))


def audit(df: pd.DataFrame, test_seasons: list[int], td_single: bool,
          seed: int = 2026, boots: int = 300) -> dict:
    rng = np.random.default_rng(seed)
    tup = tuple((s, d.STAT_FAMILY[s]) for s in STATS)
    published = pit_backtest(df[~df.season.isin(test_seasons)],
                             df[df.season.isin(test_seasons)], tup)
    train = df[df.season < min(test_seasons)]            # strictly past -> future
    test = df[df.season.isin(test_seasons)]
    out = []
    for stat in STATS:
        us, recs = [], []
        for pid, g in test.groupby("player_id"):
            fit = M.fit_player(train, pid, stat, d.STAT_FAMILY[stat], min_games=12)
            if fit is None:
                continue
            y = g[stat].dropna().astype(float).to_numpy()
            if not len(y):
                continue
            p_act = 1.0 if (td_single and fit.family == "poisson") else fit.p_active
            hi = model_cdf(fit, y, p_act)
            lo = model_cdf(fit, y - 1, p_act) if stat in DISCRETE else np.where(y <= 0, 0.0, hi)
            us.append(lo + rng.uniform(size=len(y)) * (hi - lo))
            hist = train.loc[train.player_id == pid, stat].dropna().astype(float)
            line = 0.5 if stat in DISCRETE else float(np.floor(hist.median())) + 0.5
            p_over = float(1.0 - model_cdf(fit, [line], p_act)[0])
            base = (float((hist > line).sum()) + 1.0) / (len(hist) + 2.0)   # Laplace-smoothed
            recs.append(pd.DataFrame({"pid": pid, "p": p_over, "base": base,
                                      "hit": (y > line).astype(float)}))
        if not recs:
            continue
        u = np.concatenate(us)
        r = pd.concat(recs, ignore_index=True)
        groups = {k: v for k, v in r.groupby("pid")}
        pids = np.array(list(groups))
        gaps = []
        for _ in range(boots):
            s = pd.concat([groups[k] for k in rng.choice(pids, len(pids))])
            gaps.append(s.hit.mean() - s.p.mean())
        lo95, hi95 = (float(x) for x in np.percentile(gaps, [2.5, 97.5]))
        gap = float(r.hit.mean() - r.p.mean())
        brier = float(((r.p - r.hit) ** 2).mean())
        brier_base = float(((r.base - r.hit) ** 2).mean())
        bss = 1.0 - brier / brier_base if brier_base > 0 else float("nan")
        passes = ((lo95 <= 0 <= hi95) or abs(gap) <= GATE["max_abs_gap"]) and bss > 0 \
            and len(pids) >= GATE["min_players"] and len(r) >= GATE["min_games"]
        pub = published[published.stat == stat]
        out.append({
            "stat": stat, "player_games": len(r), "players": len(pids),
            "published_mean_u": float(pub.mean_u.iloc[0]) if len(pub) else None,
            "randomized_mean_u": float(u.mean()),
            "pred_p_over": float(r.p.mean()), "actual_hit": float(r.hit.mean()),
            "gap": gap, "gap_ci95": [lo95, hi95], "brier": brier,
            "brier_baseline": brier_base, "brier_skill": bss,
            "gate": "PASS" if passes else "FAIL",
        })
    return {"as_of": date.today().isoformat(), "test_seasons": test_seasons, "train": f"seasons < {min(test_seasons)}",
            "td_single_inflation": td_single, "gate_thresholds": GATE, "stats": out}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stats_csv")
    ap.add_argument("--test", type=int, nargs="+", default=[2022, 2023])
    ap.add_argument("--td-single-inflation", action="store_true",
                    help="score TDs with the Poisson applied once (the proposed fix)")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    res = audit(d.load_stats(a.stats_csv), a.test, a.td_single_inflation)
    cols = ["stat", "players", "player_games", "published_mean_u", "randomized_mean_u",
            "pred_p_over", "actual_hit", "gap", "brier", "brier_baseline", "brier_skill", "gate"]
    t = pd.DataFrame(res["stats"])
    t["gap_ci95"] = t.gap_ci95.map(lambda c: f"[{c[0]:+.3f},{c[1]:+.3f}]")
    print(f"train {res['train']} | test {res['test_seasons']} | "
          f"TD single inflation: {res['td_single_inflation']}")
    print(t[cols + ["gap_ci95"]].round(3).to_string(index=False))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
