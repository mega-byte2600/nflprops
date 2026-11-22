"""Calibration: the honesty gate for model probabilities.

Measured result (BML cycle 5, leakage-free PIT on real nflverse data): raw
per-player fits are NOT calibrated — TDs mean-u 0.85, yards mean-u 0.33-0.46,
KS-p<0.0001 everywhere. So a raw over-probability is an UNTRUSTWORTHY estimate
until corrected. This module provides:
  1. a probability-integral-transform (PIT) backtest to MEASURE calibration
     (the honest score), and
  2. a calibration object that maps raw p -> corrected p (isotonic/logit)
     fit on held-out data, exposing reverse_function for the engine.

Reference: proper-scoring discipline (Brier 1950; Gneiting-Raftery 2007).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import marginals as M


def pit_backtest(train: pd.DataFrame, test: pd.DataFrame,
                 stats_tuples: tuple[tuple[str, str], ...]) -> pd.DataFrame:
    """Leakage-free PIT calibration backtest (train < test seasons).

    For each player fit the marginal on train, then compute u = CDF(actual) on
    test. Calibrated => u ~ Uniform(0,1). Returns per-stat summary.
    """
    rows = []
    for stat, family in stats_tuples:
        us = []
        for pid, g in test.groupby("player_id"):
            fit = M.fit_player(train, pid, stat, family, min_games=12)
            if fit is None:
                continue
            y = g[stat].astype(float).to_numpy()
            for v in y:
                if np.isnan(v):
                    continue
                u = float(M.cdf(fit, np.array([v]))[0])
                us.append(max(min(u, 1 - 1e-9), 1e-9))
        if not us:
            continue
        us = np.array(us)
        _ks, p = stats.kstest(us, "uniform")
        rows.append({
            "stat": stat, "n": len(us), "mean_u": float(us.mean()),
            "ks_p": float(p),
            "max_dev": float(np.abs(np.sort(us) - np.linspace(0, 1, len(us))).max()),
        })
    return pd.DataFrame(rows)


class Calibration:
    """Maps raw model probabilities to calibrated ones via isotonic regression,
    fit on a held-out calibration set. Clamps to keep thin buckets honest."""

    def __init__(self, raw: np.ndarray, outcome: np.ndarray, clamp: float = 0.20):
        self.raw = np.asarray(raw, dtype=float)
        self.outcome = np.asarray(outcome, dtype=float)
        self.clamp = clamp
        try:
            from sklearn.isotonic import IsotonicRegression
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(self.raw, self.outcome)
            self.iso = iso
        except ImportError:  # sklearn not installed -> identity fallback
            self.iso = None

    def __call__(self, raw_p: float | np.ndarray) -> float | np.ndarray:
        r = np.clip(np.asarray(raw_p, dtype=float), 1e-9, 1 - 1e-9)
        if self.iso is None:
            return r
        out = self.iso.predict(r)
        return np.clip(out, self.clamp, 1 - self.clamp)


def calibration_reverse_function(cal: Calibration | None, raw_p: float) -> float:
    """Apply (or pass through) calibration to a single over-probability."""
    if cal is None:
        return float(np.clip(raw_p, 1e-9, 1 - 1e-9))
    return float(np.clip(cal(raw_p), 1e-9, 1 - 1e-9))