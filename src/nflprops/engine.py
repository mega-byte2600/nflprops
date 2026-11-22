"""Engine: orchestrate per-player marginals -> Gaussian copula -> Monte Carlo.

Produces, for a player, correlated sampled stat vectors with median/mean and
a 90% CI, plus the honest over-probability P(stat > line) for any user line.
A broken-out seam accepts a calibration-correction and line-anchor (the
closing-line prior) — raw fits are NOT calibrated (see calibration.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import copula
from . import data as d
from . import marginals as M
from .calibration import calibration_reverse_function


@dataclass
class Player:
    player_id: str
    name: str | None = None
    fits: dict[str, M.Marginal] = field(default_factory=dict)


@dataclass
class PropForecast:
    stat: str
    line: float
    df: pd.DataFrame            # simulated stat column + __u col
    samples: np.ndarray        # simulated stat values
    p_active: float
    p_over: float               # P(stat > line), after calibration if applied
    median: float
    mean: float
    ci90: tuple[float, float]


class Engine:
    """The honest decision engine: marginals + copula + Monte Carlo + CI."""

    def __init__(self, df: pd.DataFrame, seed: int = 42):
        self.df = df
        self.rng = np.random.default_rng(seed)
        self.stats = list(copula.DEFAULT_STATS)
        self.corr = copula.spearman_matrix(df, self.stats)
        self.cop = copula.GaussianCopula(self.corr, self.stats)
        self._cache: dict[str, Player] = {}

    def player(self, player_id: str) -> Player:
        if player_id not in self._cache:
            fits = M.fit_many(self.df, player_id, self.stats)
            name = d.get_names(self.df).get(player_id)
            self._cache[player_id] = Player(player_id, name, fits)
        return self._cache[player_id]

    def simulate(self, player_id: str, n: int = 10000,
                 calibration_curve: object | None = None) -> dict[str, np.ndarray]:
        """Correlated sample of all fitted stats for one player."""
        return self.cop.sample(
            lambda pid, stat: self.player(player_id).fits.get(stat), player_id, n, self.rng)

    def forecast(self, player_id: str, stat: str, line: float, n: int = 10000,
                 calibration: object | None = None) -> PropForecast | None:
        """Forecast P(stat > line) with Monte Carlo + optional calibration.

        Pass a Calibration (from nflprops.calibration) to correct the raw
        over-probability; raw fits are NOT calibrated out of the box (the PIT
        backtest measures this) so calibration should be applied for real use.
        """
        fit = self.player(player_id).fits.get(stat)
        if fit is None:
            return None
        samples = self.simulate(player_id, n).get(stat)
        if samples is None:
            return None
        raw = float((samples > line).mean())
        p_over = calibration_reverse_function(calibration, raw) if calibration else raw
        return PropForecast(
            stat=stat, line=line,
            df=pd.DataFrame({stat: samples}),
            samples=samples, p_active=fit.p_active, p_over=p_over,
            median=float(np.median(samples)),
            mean=float(samples.mean()),
            ci90=(float(np.percentile(samples, 5)), float(np.percentile(samples, 95))),
        )