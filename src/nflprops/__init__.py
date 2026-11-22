"""nflprops - NFL player-prop decision engine.

Honest framing (see README): this does NOT guarantee winners. It prices props
with a calibrated probability, sizes a fractional-Kelly stake, and reports the
variance. The only real edge is finding value vs a de-vigged market and
executing well (line shopping + CLV).
"""
from .calibration import Calibration, pit_backtest
from .copula import GaussianCopula, spearman_matrix
from .data import STAT_FAMILY, ensure_cache, load_stats, resolve_player
from .elite import (
    defense_strength,
    load_pbp,
    neutral_script_mask,
    opponent_adjusted,
    partial_pool,
    ratings,
    team_context_pool,
    team_implied_mean,
)
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
from .simulator import (
    FieldPositionStratifiedDriveSampler,
    PossessionSimulator,
    drive_points,
    load_drive_table,
)
from .strike import (
    anchored_over_probability,
    rank_strike_candidates,
    simulate_matchup_total,
    strike_signal,
)

__version__ = "0.1.0"
__all__ = [
    "STAT_FAMILY",
    "Calibration",
    "Engine",
    "FieldPositionStratifiedDriveSampler",
    "GaussianCopula",
    "Marginal",
    "Player",
    "PossessionSimulator",
    "PropForecast",
    "american_to_prob",
    "anchored_over_probability",
    "clv_signal",
    "defense_strength",
    "drive_points",
    "edge",
    "ensure_cache",
    "ev",
    "fit_player",
    "fractional_kelly_stake",
    "kelly_fraction",
    "load_drive_table",
    "load_pbp",
    "load_stats",
    "neutral_script_mask",
    "opponent_adjusted",
    "over_prob",
    "partial_pool",
    "pit_backtest",
    "prob_to_american",
    "quantile",
    "rank_strike_candidates",
    "ratings",
    "resolve_player",
    "simulate_matchup_total",
    "spearman_matrix",
    "strike_signal",
    "team_context_pool",
    "team_implied_mean",
]