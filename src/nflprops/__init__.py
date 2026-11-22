"""nflprops - NFL player-prop decision engine.

Honest framing (see README): this does NOT guarantee winners. It prices props
with a calibrated probability, sizes a fractional-Kelly stake, and reports the
variance. The only real edge is finding value vs a de-vigged market and
executing well (line shopping + CLV).
"""
from .calibration import Calibration, pit_backtest
from .copula import GaussianCopula, spearman_matrix
from .data import STAT_FAMILY, ensure_cache, load_stats
from .engine import Engine, Player, PropForecast
from .marginals import Marginal, fit_player, over_prob, quantile
from .odds import (
                   american_to_prob,
                   clv_signal,
                   edge,
                   ev,
                   fractional_kelly_stake,
                   kelly_fraction,
                   prob_to_american,
)

__version__ = "0.1.0"
__all__ = [
                   "STAT_FAMILY",
                   "Calibration",
                   "Engine",
                   "GaussianCopula",
                   "Marginal",
                   "Player",
                   "PropForecast",
                   "american_to_prob",
                   "clv_signal",
                   "edge",
                   "ensure_cache",
                   "ev",
                   "fit_player",
                   "fractional_kelly_stake",
                   "kelly_fraction",
                   "load_stats",
                   "over_prob",
                   "pit_backtest",
                   "prob_to_american",
                   "quantile",
                   "spearman_matrix",
]