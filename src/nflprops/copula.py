"""Gaussian copula over a player's correlated stats (Nelsen 2006).

The prop market only prices each stat's MARGINAL; the joint dependence
(receptions <-> receiving yards, rush yards <-> rush TDs) must come from
history (dkori measurement + our BML cycle-4). This module estimates a
pairwise Spearman correlation matrix on real nflverse data, projects it to
PSD, and drives a correlated sampler via a multivariate normal -> normal-CDF
-> per-marginal inverse-CDF.

Cycle-4 measured anchors (real data): receiving_yds<->receptions +0.81;
passing_yds<->receptions -0.50; receiving_yds<->receiving_TD +0.26;
rush_yds<->rush_TD +0.26; passing_yds<->passing_TD +0.43.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_STATS = ("passing_yards", "rushing_yards", "receiving_yards",
                 "receptions", "passing_tds", "rushing_tds", "receiving_tds")


def spearman_matrix(df: pd.DataFrame, stats: tuple[str, ...] = DEFAULT_STATS,
                    min_pairs: int = 200) -> np.ndarray:
    """Pairwise Spearman correlation between every pair of stats on player-games."""
    n = len(stats)
    R = np.eye(n)
    for i, a in enumerate(stats):
        for j in range(i + 1, n):
            b = stats[j]
            d = df[[a, b]].dropna()
            d = d[(d[a] > 0) & (d[b] > 0)]
            if len(d) < min_pairs:
                continue
            from scipy.stats import spearmanr
            r, _ = spearmanr(d[a], d[b])
            R[i, j] = R[j, i] = float(r)
    return R


def to_psd(S: np.ndarray, reg: float = 1e-3) -> np.ndarray:
    """Nearest-correlation-like PSD: clip negative/near-zero eigenvalues + ridge."""
    ev, V = np.linalg.eigh(S)
    ev = np.clip(ev, reg, None)
    return (V * ev) @ V.T


class GaussianCopula:
    """Samples dependent draws by relaying a multivariate normal through
    each stat's marginal via the probability integral transform."""

    def __init__(self, corr: np.ndarray, stats: tuple[str, ...] = DEFAULT_STATS):
        if corr.shape != (len(stats), len(stats)):
            raise ValueError("corr must be len(stats) x len(stats)")
        self.corr = to_psd(np.asarray(corr, dtype=float))
        self.stats = list(stats)
        self._mean = np.zeros(len(stats))

    def uniforms(self, n: int, rng: np.random.Generator | None = None) -> np.ndarray:
        """n x k matrix of dependent standard-uniform draws (the copula)."""
        rng = rng or np.random.default_rng()
        z = rng.multivariate_normal(self._mean, self.corr, size=n)
        from scipy.stats import norm
        return norm.cdf(z)

    def sample(self, marginal_for: callable, player_id: str, n: int = 10000,
               rng: np.random.Generator | None = None) -> dict[str, np.ndarray]:
        """Correlated samples for each stat.

        marginal_for: callable(stat) -> Marginal fit for this player (or None).
        Returns {stat: ndarray(n)} for each stat that has a fit, plus the
        uniforms used (key "__u") for verification.
        """
        rng = rng or np.random.default_rng()
        u = self.uniforms(n, rng)
        out: dict[str, np.ndarray] = {}
        for k, stat in enumerate(self.stats):
            fit = marginal_for(player_id, stat)
            if fit is None:
                continue
            inv = _inverse_active(fit, u[:, k])
            gate = rng.random(n) < fit.p_active          # zero-inflation gate
            out[stat] = np.where(gate, np.where(inv > 0, inv, 0.0), 0.0)
        out["__u"] = u
        return out


def _inverse_active(fit, u: np.ndarray) -> np.ndarray:
    """Inverse-CDF of the ACTIVE distribution at copula uniforms u."""
    from scipy import stats
    # reproduce the per-family quantile sampling without the zero gate
    if fit.family == "gamma_zinf":
        sh, sc = fit.params
        return stats.gamma.ppf(u, sh, 0, sc)
    if fit.family == "normal_zinf":
        mu, sd = fit.params
        return stats.norm.ppf(u, mu, sd)
    if fit.family == "poisson":
        (lam,) = fit.params
        return stats.poisson.ppf(u, lam)
    r, p = fit.params
    return stats.nbinom.ppf(u, r, p)