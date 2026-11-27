"""Evaluate projection v2 against the ADR-0003 gate on real nflverse data.

Tuning and recalibration use validation seasons only; the test windows are never touched
until the final scoring. Every prediction is one-step-ahead (prior games only).

    python scripts/model_v2_eval.py --legacy cache/player_stats.csv \
        --current cache/stats_player_week_2025.csv cache/stats_player_week_2026.csv \
        --games cache/games.csv [--json docs/audit/latest.json]
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import date

import numpy as np
import pandas as pd

from nflprops import projection as P
from nflprops import sources as S

VALID = (2019, 2020, 2021)
TESTS = {"2022-23": (2022, 2023), "2024-26": (2024, 2025, 2026)}
GATE_WINDOW = "2024-26"
GRID_H, GRID_K, GRID_B, GRID_NU = (4, 8, 16, 32), (2, 5, 10, 20), (0.0, 0.5, 1.0), (2, 4, 8, 32)


def _boot(r: pd.DataFrame, rng, n: int = 1000):
    """Player-clustered bootstrap. Tuned parameters and recalibration maps are held fixed,
    so these CIs slightly understate total uncertainty (disclosed in the audit)."""
    groups = list(r.groupby("player_id").indices.values())
    gaps, s_cal, s_stk = [], [], []
    for _ in range(n):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        s = r.iloc[idx]
        gaps.append(s.y1.mean() - s.p.mean())
        s_cal.append(1 - P.brier(s.p, s.y1) / P.brier(s.base_cal, s.y1))
        s_stk.append(1 - P.brier(s.p, s.y1) / P.brier(s.base_stk, s.y1))
    pct = lambda a: [float(x) for x in np.percentile(a, [2.5, 97.5])]
    return pct(gaps), pct(s_cal), pct(s_stk)


def run(weeks: pd.DataFrame, implied: pd.DataFrame, seed: int = 2026) -> dict:
    rng = np.random.default_rng(seed)
    out = []
    for si, stat in enumerate(P.STATS):
        rng = np.random.default_rng([seed, si])   # per-stat stream: order-independent CIs
        td = stat in P.TDS
        base_frame = P.frame(weeks, implied, stat)
        best = None
        for h in GRID_H:
            feat = P.features(base_frame, h, td)
            for k, b in itertools.product(GRID_K, GRID_B):
                loc = P.location(feat, stat, P.Params(h, k, b))
                val = loc[loc.season.isin(VALID)]
                disp = P.dispersion(val, stat)
                for nu in (GRID_NU if td else (None,)):
                    p = P.p_over(val, stat, disp, nu or 4.0)
                    score = P.brier(p, (val.y > val.line).astype(float).to_numpy())
                    if best is None or score < best[0]:
                        best = (score, h, k, b, nu, disp, loc)
        _, h, k, b, nu, disp, loc = best
        loc = loc.copy()
        loc["p_raw"] = P.p_over(loc, stat, disp, nu or 4.0)
        loc["y1"] = (loc.y > loc.line).astype(float)
        val = loc[loc.season.isin(VALID)]
        cal = P.Platt(val.p_raw.to_numpy(), val.y1.to_numpy())
        loc["p"] = cal(loc.p_raw.to_numpy())
        # Baselines get the SAME held-out treatment as the model (review finding 1):
        bcal = P.Platt(val.base.to_numpy(), val.y1.to_numpy())
        loc["base_cal"] = bcal(loc.base.to_numpy())
        stk = P.Logistic(P.stacked_features(val), val.y1.to_numpy())
        loc["base_stk"] = stk(P.stacked_features(loc))
        row = {"stat": stat, "params": {"h": h, "k": k, "beta": b, "nu": nu, "disp": disp,
                                        "platt_a": float(cal.a), "platt_b": float(cal.b)}}
        for name, seasons in TESTS.items():
            r = loc[loc.season.isin(seasons)].reset_index(drop=True)
            gap_ci, cal_ci, stk_ci = _boot(r, rng)
            row[name] = {"player_games": len(r), "players": int(r.player_id.nunique()),
                         "pred": float(r.p.mean()), "actual": float(r.y1.mean()),
                         "gap": float(r.y1.mean() - r.p.mean()), "gap_ci95": gap_ci,
                         "brier": P.brier(r.p, r.y1),
                         "skill_vs_naive_cal": 1 - P.brier(r.p, r.y1) / P.brier(r.base_cal, r.y1),
                         "skill_vs_naive_cal_ci95": cal_ci,
                         "skill_vs_stacked": 1 - P.brier(r.p, r.y1) / P.brier(r.base_stk, r.y1),
                         "skill_vs_stacked_ci95": stk_ci,
                         "skill_vs_naive_uncalibrated":
                             1 - P.brier(r.p, r.y1) / P.brier(r.base, r.y1)}
        row["per_season"] = {}
        for season in TESTS[GATE_WINDOW]:
            r = loc[loc.season == season]
            row["per_season"][str(season)] = {
                "player_games": len(r), "gap": float(r.y1.mean() - r.p.mean()),
                "skill_vs_naive_cal": 1 - P.brier(r.p, r.y1) / P.brier(r.base_cal, r.y1)}
        # ADR-0003 window: the most recent seasons, pooled per stat until >= 1000 player-games
        win, n = [], 0
        for season in sorted(loc.season.unique(), reverse=True):
            if season in VALID or n >= 1000:
                break
            win.append(int(season))
            n += int((loc.season == season).sum())
        r = loc[loc.season.isin(win)].reset_index(drop=True)
        gap_ci, cal_ci, stk_ci = _boot(r, rng)
        g = {"seasons": sorted(win), "player_games": len(r), "players": int(r.player_id.nunique()),
             "gap": float(r.y1.mean() - r.p.mean()), "gap_ci95": gap_ci,
             "skill_vs_naive_cal": 1 - P.brier(r.p, r.y1) / P.brier(r.base_cal, r.y1),
             "skill_vs_naive_cal_ci95": cal_ci,
             "skill_vs_stacked": 1 - P.brier(r.p, r.y1) / P.brier(r.base_stk, r.y1),
             "skill_vs_stacked_ci95": stk_ci}
        row["gate_window"] = g
        calibrated = (g["gap_ci95"][0] <= 0 <= g["gap_ci95"][1]) or abs(g["gap"]) <= 0.02
        row["gate"] = "PASS" if (calibrated and g["skill_vs_naive_cal_ci95"][0] > 0
                                 and g["players"] >= 50 and g["player_games"] >= 1000) else "FAIL"
        row["beats_stacked_baseline"] = bool(g["skill_vs_stacked_ci95"][0] > 0)
        row["label"] = ("decision-grade" if row["gate"] == "PASS" and row["beats_stacked_baseline"]
                        else "modest edge" if row["gate"] == "PASS" else "experimental")
        out.append(row)
    return {"as_of": date.today().isoformat(), "model": "projection-v2",
            "validation": list(VALID), "tests": {k: list(v) for k, v in TESTS.items()},
            "gate_window": "per stat: most recent seasons pooled to >= 1000 player-games (ADR-0003)",
            "stats": out}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy", required=True)
    ap.add_argument("--current", nargs="*", default=[])
    ap.add_argument("--games", required=True)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    weeks = S.player_weeks(pd.read_csv(a.legacy, low_memory=False),
                           [pd.read_csv(c, low_memory=False) for c in a.current])
    implied = S.implied_team_totals(pd.read_csv(a.games))
    j = weeks.merge(implied, left_on=["season", "week", "recent_team"],
                    right_on=["season", "week", "team"], how="left")
    reg = j[j.season_type == "REG"]
    print(f"player-weeks {len(weeks):,} seasons {weeks.season.min()}-{weeks.season.max()} | "
          f"implied-total join coverage (REG) {reg.implied.notna().mean():.1%}")
    res = run(weeks, implied)
    for name in TESTS:
        print(f"\nTest {name} (tuned + recalibrated on {VALID[0]}-{VALID[-1]} only):")
        f = "[{:+.3f},{:+.3f}]".format
        rows = [{"stat": r["stat"], "games": r[name]["player_games"], "pred": r[name]["pred"],
                 "actual": r[name]["actual"], "gap": r[name]["gap"],
                 "gap_ci95": f(*r[name]["gap_ci95"]),
                 "skill_naive_cal": r[name]["skill_vs_naive_cal"],
                 "ci95": f(*r[name]["skill_vs_naive_cal_ci95"]),
                 "skill_stacked": r[name]["skill_vs_stacked"],
                 "ci95_stk": f(*r[name]["skill_vs_stacked_ci95"])} for r in res["stats"]]
        print(pd.DataFrame(rows).round(3).to_string(index=False))
    print("\nParams + gate (" + GATE_WINDOW + "):")
    for r in res["stats"]:
        ps = " ".join(f"{k}: n={v['player_games']} gap={v['gap']:+.3f} skill={v['skill_vs_naive_cal']:+.3f}"
                      for k, v in r["per_season"].items())
        g = r["gate_window"]
        f2 = "[{:+.3f},{:+.3f}]".format
        print(f"  {r['stat']:16s} {r['gate']} -> {r['label']:14s} window {g['seasons']} n={g['player_games']}"
              f" gap={g['gap']:+.3f} {f2(*g['gap_ci95'])} skill_naive={g['skill_vs_naive_cal']:+.3f}"
              f" {f2(*g['skill_vs_naive_cal_ci95'])} skill_stacked={g['skill_vs_stacked']:+.3f}"
              f" {f2(*g['skill_vs_stacked_ci95'])}")
        print(f"      per season: {ps}")
        print("      "
              + json.dumps({k: (round(v, 3) if isinstance(v, float) else v)
                            for k, v in r["params"].items()}))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
