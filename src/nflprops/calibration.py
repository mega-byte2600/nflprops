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

DISCRETE_FAMILIES = {"poisson", "nb"}


def randomized_pit(fit: M.Marginal, y: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Randomized PIT (Czado, Gneiting & Held 2009) against the sampled mixture.

    u = F(y-) + V * (F(y) - F(y-)), V ~ U(0,1). Uniform(0,1) for a correctly specified model,
    including at the zero atom and for integer counts, where the plain u = F(y) is not.
    """
    y = np.asarray(y, dtype=float)
    hi = M.mixture_cdf(fit, y)
    if fit.family in DISCRETE_FAMILIES:
        lo = M.mixture_cdf(fit, y - 1)
    else:
        lo = np.where(y <= 0, 0.0, hi)
    return lo + rng.uniform(size=len(y)) * (hi - lo)


def pit_backtest(train: pd.DataFrame, test: pd.DataFrame,
                 stats_tuples: tuple[tuple[str, str], ...], seed: int = 0) -> pd.DataFrame:
    """Temporal PIT calibration backtest (ADR-0003).

    For each player fit the marginal on `train` (callers pass seasons strictly before the
    test seasons), then score each test game with the randomized PIT. Calibrated means
    u ~ Uniform(0,1). The KS p-value treats player-games as independent, so it is
    descriptive only; the gate uses player-clustered CIs (scripts/calibration_audit.py).
    """
    rng = np.random.default_rng(seed)
    rows = []
    for stat, family in stats_tuples:
        us = []
        for pid, g in test.groupby("player_id"):
            fit = M.fit_player(train, pid, stat, family, min_games=12)
            if fit is None:
                continue
            y = g[stat].dropna().astype(float).to_numpy()
            if len(y):
                us.append(randomized_pit(fit, y, rng))
        if not us:
            continue
        us = np.clip(np.concatenate(us), 1e-9, 1 - 1e-9)
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