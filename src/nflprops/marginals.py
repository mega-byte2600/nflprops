"""Per-player marginal distribution fits (MEASURED families, zero-inflated).

BML background (see docs/BML_LOOP.md and the nfl-prop-betting skill):
- Yards: rushing/receiving -> gamma (right-skew +1.7), passing -> normal.
- Counts: TDs -> Poisson per player (median dispersion ~1.0); receptions ->
  NB only if overdispersed (disp>1.15), else Poisson (54% of players
  overdispersed, i.e. split).
- All continuous fits are ZERO-INFLATED: fit on active games then gate by
  P(active), because gamma/normal reject 0-yard games.
CAUTION (measured): raw per-player fits are NOT calibrated out of the box
(cycle-5 PIT: TDs mean-u 0.85, yards 0.33-0.46). This module returns the raw
fit; calibration/anchor correction happens in the engine layer.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from . import data as d


@dataclass
class Marginal:
    """A fitted per-player marginal distribution."""
    stat: str
    family: str          # gamma_zinf / normal_zinf / poisson / nb
    params: tuple        # (shape, scale) | (mu, sd) | (lambda,) | (r, p)
    p_active: float      # P(usage>0) for zero-inflation
    n: int               # games used to fit


def nb_mom(x: np.ndarray) -> tuple[float, float] | None:
    """Method-of-moments negative binomial (r, p). None if underdispersed."""
    mu = float(x.mean()); var = float(x.var(ddof=1))
    if var <= mu + 1e-9 or mu <= 0:
        return None
    p = mu / var
    r = mu * p / (1 - p)
    if r <= 0 or p <= 0 or p >= 1:
        return None
    return r, p


def fit_player(df: pd.DataFrame, player_id: str, stat: str, family: str,
               min_games: int = 8) -> Marginal | None:
    """Fit one stat for one player on their real game history."""
    x = df[(df["player_id"] == player_id) & df[stat].notna()][stat].astype(float).to_numpy()
    if len(x) < min_games or x.mean() <= 0:
        return None
    pos = x[x > 0]
    ppos = float(len(pos) / len(x))
    if len(pos) < min_games:
        return None

    if family == "gamma":                      # rush/rec yards
        shape, _, scale = stats.gamma.fit(pos, floc=0)
        if not (shape > 0 and scale > 0):
            return None
        return Marginal(stat, "gamma_zinf", (float(shape), float(scale)), ppos, len(x))
    if family == "normal":                     # passing yards
        mu, sd = pos.mean(), pos.std(ddof=1)
        if sd <= 0:
            return None
        return Marginal(stat, "normal_zinf", (float(mu), float(sd)), ppos, len(x))
    # Count families are fit on ALL games (zeros included), so they already carry the zero
    # mass: p_active = 1.0. Gating them again double-counts zeros (audit 2026-11-27: anytime
    # TD 0.116 predicted vs 0.274 actual).
    if family == "poisson":                    # TDs
        return Marginal(stat, "poisson", (float(x.mean()),), 1.0, len(x))
    if family == "dispersion-gated-nb":        # receptions
        disp = float(x.var(ddof=1) / x.mean())
        mom = nb_mom(x)
        if disp > 1.15 and mom is not None:
            return Marginal(stat, "nb", mom, 1.0, len(x))
        return Marginal(stat, "poisson", (float(x.mean()),), 1.0, len(x))
    raise ValueError(f"unknown family {family}")


def fit_many(df: pd.DataFrame, player_id: str,
             stats: tuple[str, ...] | None = None) -> dict[str, Marginal]:
    """Fit a full vector of correlated stats for one player."""
    stats = stats or tuple(d.STAT_FAMILY)
    fits: dict[str, Marginal] = {}
    for s in stats:
        f = fit_player(df, player_id, s, d.STAT_FAMILY[s])
        fits[s] = f
    return fits


def rvs(fit: Marginal, n: int, rng: np.random.Generator | None = None) -> np.ndarray:
    """Sample n draws from a fitted marginal, applying the zero-inflation gate."""
    rng = rng or np.random.default_rng()
    u = rng.random(n)
    if fit.family == "gamma_zinf":
        sh, sc = fit.params
        v = stats.gamma.ppf(u, sh, 0, sc)
    elif fit.family == "normal_zinf":
        mu, sd = fit.params
        v = stats.norm.ppf(u, mu, sd)
    elif fit.family == "poisson":
        (lam,) = fit.params
        v = stats.poisson.ppf(u, lam)
    else:  # nb
        r, p = fit.params
        v = stats.nbinom.ppf(u, r, p)
    # zero-inflation: with prob (1 - p_active) force a 0
    gate = rng.random(n) < fit.p_active
    return np.where(gate, np.where(v > 0, v, 0.0), 0.0)


def cdf(fit: Marginal, vals: np.ndarray) -> np.ndarray:
    """CDF of the conditional (active) distribution at vals (for later anchor)."""
    a = np.asarray(vals, dtype=float)
    if fit.family == "gamma_zinf":
        sh, sc = fit.params
        return stats.gamma.cdf(a, sh, 0, sc)
    if fit.family == "normal_zinf":
        mu, sd = fit.params
        return stats.norm.cdf(a, mu, sd)
    if fit.family == "poisson":
        (lam,) = fit.params
        return stats.poisson.cdf(np.floor(a), lam)
    r, p = fit.params
    return stats.nbinom.cdf(np.floor(a), r, p)


def mixture_cdf(fit: Marginal, vals) -> np.ndarray:
    """CDF of exactly what rvs samples: 0 w.p. 1 - p_active, else max(active draw, 0)."""
    a = np.asarray(vals, dtype=float)
    return np.where(a < 0, 0.0, (1 - fit.p_active) + fit.p_active * cdf(fit, a))


def over_prob(fit: Marginal, line: float) -> float:
    """P(min(stat, active) > line) accounting for zero-inflation.

    P(over) = P(active) * (1 - CDF_active(line)). This is the probability a
    line priced at `line` is beaten, the quantity a prop market prices.
    """
    if line < 0:
        return fit.p_active
    return fit.p_active * (1.0 - float(cdf(fit, np.array([line]))[0]))


def quantile(fit: Marginal, q: float) -> float:
    """q-th quantile of the ACTIVE distribution (usage>0 given)."""
    if fit.family == "gamma_zinf":
        sh, sc = fit.params
        return float(stats.gamma.ppf(q, sh, 0, sc))
    if fit.family == "normal_zinf":
        mu, sd = fit.params
        return float(stats.norm.ppf(q, mu, sd))
    if fit.family == "poisson":
        (lam,) = fit.params
        return float(stats.poisson.ppf(q, lam))
    r, p = fit.params
    return float(stats.nbinom.ppf(q, r, p))