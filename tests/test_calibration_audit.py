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


def test_package_randomized_pit_is_uniform_for_perfect_models():
    from nflprops.calibration import randomized_pit
    rng = np.random.default_rng(3)
    n = 80_000
    cases = [
        (Marginal("rushing_tds", "poisson", (0.4,), 1.0, n), rng.poisson(0.4, n).astype(float)),
        (Marginal("rushing_yards", "gamma_zinf", (2.0, 20.0), 0.7, n),
         np.where(rng.uniform(size=n) < 0.7, rng.gamma(2.0, 20.0, n), 0.0)),
    ]
    for fit, y in cases:
        u = randomized_pit(fit, y, rng)
        assert abs(u.mean() - 0.5) < 0.01, fit.family


def test_count_fits_do_not_double_inflate_zeros():
    import pandas as pd

    from nflprops.marginals import fit_player, over_prob
    rng = np.random.default_rng(4)
    y = rng.poisson(0.5, 400).astype(float)
    df = pd.DataFrame({"player_id": "p", "rushing_tds": y})
    fit = fit_player(df, "p", "rushing_tds", "poisson")
    assert fit.p_active == 1.0
    assert abs(over_prob(fit, 0.5) - (y > 0.5).mean()) < 0.05


def test_randomized_pit_handles_negative_yards_as_the_zero_atom():
    from nflprops.calibration import randomized_pit
    rng = np.random.default_rng(5)
    n, mu, sd, p_act = 80_000, 20.0, 25.0, 0.9
    v = rng.normal(mu, sd, n)                          # includes negative yardage games
    y = np.where(rng.uniform(size=n) < p_act, v, 0.0)  # what the field produces
    fit = Marginal("rushing_yards", "normal_zinf", (mu, sd), p_act, n)
    u = randomized_pit(fit, y, rng)
    assert abs(u.mean() - 0.5) < 0.01
