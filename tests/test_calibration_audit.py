"""Self-validation of the ADR-0003 scorer: a perfectly specified model must score as calibrated.

Hermetic (synthetic data only). Guards against the measurement artifacts found in the
2026-11-27 audit: non-randomized PIT on counts and a PIT that ignores zero-inflation.
"""
import importlib.util
from pathlib import Path

import numpy as np

from nflprops.marginals import Marginal

_spec = importlib.util.spec_from_file_location(
    "calibration_audit", Path(__file__).resolve().parent.parent / "scripts/calibration_audit.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


def _randomized_u(fit, y, p_active, discrete, rng):
    hi = audit.model_cdf(fit, y, p_active)
    lo = audit.model_cdf(fit, y - 1, p_active) if discrete else np.where(y <= 0, 0.0, hi)
    return lo + rng.uniform(size=len(y)) * (hi - lo)


def test_perfect_poisson_scores_calibrated_only_when_randomized():
    rng = np.random.default_rng(1)
    lam = 0.35
    y = rng.poisson(lam, 100_000).astype(float)
    fit = Marginal("rushing_tds", "poisson", (lam,), 1.0, len(y))
    u = _randomized_u(fit, y, 1.0, True, rng)
    assert abs(u.mean() - 0.5) < 0.01
    naive = audit.model_cdf(fit, y, 1.0)          # the published (non-randomized) PIT
    assert naive.mean() > 0.7                     # the artifact the audit found


def test_perfect_zero_inflated_gamma_scores_calibrated_with_mixture_cdf():
    rng = np.random.default_rng(2)
    p_active, shape, scale = 0.75, 2.0, 20.0
    n = 100_000
    y = np.where(rng.uniform(size=n) < p_active, rng.gamma(shape, scale, n), 0.0)
    fit = Marginal("rushing_yards", "gamma_zinf", (shape, scale), p_active, n)
    u = _randomized_u(fit, y, p_active, False, rng)
    assert abs(u.mean() - 0.5) < 0.01
    hist, _ = np.histogram(u, bins=10, range=(0, 1))
    assert (np.abs(hist / n - 0.1) < 0.01).all()  # flat reliability, not just the mean
