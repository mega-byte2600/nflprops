"""BML cycle 7 (backtest): do the elite priors improve calibration?

The real, honest BML question behind increments 1-3: does baking the team-context
prior into the per-player marginal improve OUT-OF-SAMPLE calibration, or is it
(over)shrinkage that hurts?

Method (leakage-free, given only 2023/2024 pbp exist):
  TRAIN:
     player stat marginals fit on seasons <= 2022 (player_stats.csv, 1999-2022)
     team-context prior (EPA ratings + pooled mean) fit on 2023 pbp alone
  TEST:
     2024 games (never seen during fitting).
  Compare, per stat, the PIT calibration of:
    (RAW)  the per-player marginal as fitted on train.
    (POOL) the same marginal recentered so its location = the team-context
           pooled_mean (partial pooling toward the position/team prior).
  Calibrated => PIT u ~ Uniform(0,1): mean_u near 0.5, ks_p reasonable.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as _sp

from nflprops import elite as E
from nflprops import marginals as M

CACHE = Path(__file__).resolve().parent / "cache"

# baseline marginals mirror engine/data STAT_FAMILY
FAMILY = {"passing_yards": "normal", "rushing_yards": "gamma",
          "receiving_yards": "gamma", "receptions": "dispersion-gated-nb",
          "rushing_tds": "poisson", "receiving_tds": "poisson"}


def recenter(fit: M.Marginal, target_mean: float) -> M.Marginal:
    """Shift a fit's LOCATION so its (unconditional-ish) mean = target_mean.

    Preserves family + shape/dispersion; only recenters the mean toward the
    pooled prior (the elite methodology's partial-pooling, increment 3).
    """
    t = max(0.5, float(target_mean))
    if fit.family == "gamma_zinf":
        sh, sc = fit.params          # mean = sh*sc -> scale = t/sh
        return M.Marginal(fit.stat, fit.family, (sh, t / sh), fit.p_active, fit.n)
    if fit.family == "normal_zinf":
        mu, sd = fit.params
        return M.Marginal(fit.stat, fit.family, (t, sd), fit.p_active, fit.n)
    if fit.family == "poisson":
        return M.Marginal(fit.stat, fit.family, (t,), fit.p_active, fit.n)
    if fit.family == "nb":
        r, p = fit.params            # NB mean = r(1-p)/p ; keep r, solve p
        # mean_formula: r*(1-p)/p = t -> p = r/(r+t)
        p2 = r / (r + t)
        return M.Marginal(fit.stat, fit.family, (r, max(1e-6, min(0.999, p2))), fit.p_active, fit.n)
    return fit


def pit_for_marginal(fit: M.Marginal, test: pd.DataFrame, stat: str, pid: str) -> list[float]:
    """PIT u=CDF(actual) for a player's test-season outcomes (leakage-free)."""
    us = []
    y = test[test["player_id"] == pid][stat].astype(float).to_numpy()
    for v in y:
        if np.isnan(v):
            continue
        u = float(M.cdf(fit, np.array([v]))[0])
        us.append(max(min(u, 1 - 1e-9), 1e-9))
    return us


def main() -> None:
    stats_df = pd.read_csv(CACHE / "player_stats.csv", na_values=["NA", ""],
                           low_memory=False)
    # leakage-free split: marginals on <=2022 stats, prior on 2023 pbp, test 2024
    train = stats_df[stats_df["season"] <= 2022]
    test = stats_df[stats_df["season"] == 2024]

    # team-context prior from 2023 pbp (before the 2024 test window).
    # Build a SEPARATE pooled prior per stat: team_context_pool builds the
    # prior for one stat (mean per player), so applying one stat's number to
    # all stats would be a category error. Loop stats.
    pbp = E.load_pbp(CACHE / "pbp_2023_elite.csv")
    rat = E.ratings(pbp)
    pooled_by_stat: dict[str, dict[str, float]] = {}
    for stat in FAMILY:
        pool_df = E.team_context_pool(train, rat, stat=stat)
        pooled_by_stat[stat] = dict(zip(pool_df["player_id"],
                                        pool_df["pooled_mean"]))

    players = test["player_id"].unique()
    rows = []
    for stat, family in FAMILY.items():
        raw_us, pool_us = [], []
        pooled = pooled_by_stat.get(stat, {})
        for pid in players:
            f = M.fit_player(train, pid, stat, family, min_games=10)
            if f is None:
                continue
            raw_us += pit_for_marginal(f, test, stat, pid)
            if pid in pooled:
                fp = recenter(f, pooled[pid])
                pool_us += pit_for_marginal(fp, test, stat, pid)
        def summ(us):
            us = np.array(us)
            if len(us) == 0:
                return None
            _k, p = _sp.kstest(us, "uniform")
            return (len(us), float(us.mean()), float(p),
                    float(np.abs(np.sort(us) - np.linspace(0, 1, len(us))).max()))
        r, p = summ(raw_us), summ(pool_us)
        row = {"stat": stat,
               "raw_n": r[0] if r else 0, "raw_mean_u": r[1] if r else np.nan,
               "raw_ks_p": r[2] if r else np.nan,
               "pool_n": p[0] if p else 0, "pool_mean_u": p[1] if p else np.nan,
               "pool_ks_p": p[2] if p else np.nan}
        rows.append(row)

    out = pd.DataFrame(rows)
    print("\n=== BML cycle 7: raw vs team-context-pooled PIT (marginals<=2022, prior 2023, test 2024) ===")
    print("  calibrated => mean_u ~ 0.5; KS_p against Uniform")
    print(out.round(3).to_string(index=False))
    print("\n- raw_mean_u far from 0.5 => raw fits NOT calibrated (known).")
    print("- pool_mean_u closer to 0.5 than raw on a stat => the team prior")
    print("  helps that stat OOS; farther => pooling overshrinks it (hurts).")


if __name__ == "__main__":
    main()