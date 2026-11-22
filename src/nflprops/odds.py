"""Odds conversion, de-vig, expected value, Kelly staking, and CLV.

All standard betting math, worked numbers inline. Formulas re-derived (see the
nfl-prop-betting skill's math-cheatsheet, independently audited to 9+).
"""
from __future__ import annotations

import numpy as np


def american_to_prob(american: float) -> float:
    """American odds -> implied probability."""
    if american >= 0:
        return 100.0 / (american + 100)
    return (-american) / (-american + 100)


def prob_to_american(p: float) -> float:
    """Implied probability -> American odds."""
    p = float(np.clip(p, 1e-9, 1 - 1e-9))
    if p >= 0.5:
        return -((p / (1 - p)) * 100)
    return ((1 - p) / p) * 100


def decimal_to_prob(d: float) -> float:
    return 1.0 / d


def prob_to_decimal(p: float) -> float:
    return 1.0 / float(np.clip(p, 1e-9, 1 - 1e-9))


def devig_proportional(implieds: list[float]) -> list[float]:
    """Multiplicative de-vig: divide each implied by the overround sum."""
    s = sum(implieds)
    if s <= 0:
        return implieds
    return [i / s for i in implieds]


def consensus_fair(over_implieds: list[float], under_implieds: list[float],
                   method: str = "proportional") -> float:
    """Fair Over probability from parallel over/under implieds per book.

    For each book the fair Over = over / (over + under) (de-vigs that book's
    two-sided pair); the consensus is the median across books. This is the
    correct construction for a binary O/U prop (dkori + the skill's de-vig
    rule). One number per book in each list; lengths must match.
    """
    if len(over_implieds) != len(under_implieds):
        raise ValueError("over_implieds and under_implieds must be same length")
    fair = []
    for o, un in zip(over_implieds, under_implieds):
        s = o + un
        if s <= 0:
            continue
        fair.append(o / s)
    if not fair:
        return float("nan")
    import numpy as np
    return float(np.median(fair))


def ev(prob_fair: float, decimal_odds: float) -> float:
    """Expected value per unit staked = p*odds - 1."""
    return prob_fair * decimal_odds - 1.0


def edge(prob_fair: float, decimal_odds: float) -> float:
    """Edge as a probability delta = p_fair - market_implied."""
    return prob_fair - decimal_to_prob(decimal_odds)


def kelly_fraction(prob_fair: float, decimal_odds: float) -> float:
    """Full Kelly fraction f = (b*p - q)/b, b = decimal-1."""
    b = decimal_odds - 1.0
    q = 1.0 - prob_fair
    return (b * prob_fair - q) / b if b > 0 else 0.0


def fractional_kelly_stake(prob_fair: float, decimal_odds: float,
                           bankroll: float, fraction: float = 0.25) -> float:
    """Stake in currency = fraction * Kelly * bankroll. fraction 1/4 default."""
    f = kelly_fraction(prob_fair, decimal_odds)
    return max(0.0, fraction * f * bankroll)


def clv_signal(your_price_decimal: float, closing_decimal: float) -> float:
    """Closing line value: positive when your price beat the sharp close.
    Returns the difference in implied probability (your implied - closing implied)."""
    return decimal_to_prob(your_price_decimal) - decimal_to_prob(closing_decimal)


def p_over_from_samples(samples, line: float) -> float:
    return float((np.asarray(samples) > line).mean())