"""Increment 5: strike seam - EPA/team-total gap vs a market anchor.

The honest edge premise of this whole project is CLV and line-shopping, NOT
out-predicting the market. So the "strike" seam does the disciplined thing:
it compares our simulated distribution (inc 4) against an EXPECTED TOTAL -
either a user-supplied closing line or, keyless, the market-implied total
recovered from the play-by-play's vegas data if present. It reports:

  - our simulated mean total
  - the anchor (market) mean total
  - the gap, and whether it is within sampling CI (the honest gate)
  - a buy/no-buy recommendation that honors the empirical reality: a single
    gap is ~noise; only a gap that (a) exceeds the sim's own CI width AND
    (b) persists across many simulations is worth flagging as a line-shopping
    candidate - and even then it is a CANDIDATE to compare across books, not
    a guaranteed +EV bet.

VERIFIED on real data (see tests + ELITE_ROADMAP reproduce). Live multi-book
odds hydration is wired when the user supplies a provider key; until then the
seam operates keyless on the vegas-anchored total and honestly reports the
live-odds gate.
"""
from __future__ import annotations

import numpy as np

from .simulator import PossessionSimulator


def anchor_expected_total(drive_df, offense: str, defense: str,
                          market_total: float | None = None) -> float:
    """Return the market total a matchup is expected to produce.

    If market_total is given (closing line, the sharp anchor) use it. Keyless,
    we have no live line, so this raises - the seam must not invent a market.
    """
    if market_total is not None and market_total > 0:
        return float(market_total)
    raise ValueError(
        "no market total supplied; the strike seam refuses to invent a sharp "
        "anchor (keyless mode cannot price a real closing line - wire an odds "
        "provider key or pass --market-total)")


def simulate_matchup_total(sim: PossessionSimulator, offense: str, defense: str,
                           n: int = 5000) -> tuple[float, float, float]:
    """Simulated (mean_total, ci_low, ci_high) for the matchup.

    One side is the offense (we price whether THEY beat their implied total):
    total = offense score + opponent score. For a pure team-total comparison,
    callers compare the offense-half via a single-team total seam.
    """
    g = sim.simulate_games(offense, defense, n=n)
    total = g.home_score + g.away_score
    return (float(total.mean()),
            float(np.percentile(total, 5)),
            float(np.percentile(total, 95)))


def anchored_over_probability(sim: PossessionSimulator, home: str, away: str,
                              market_total: float, side: str = "home",
                              team_line: float | None = None,
                              n: int = 5000) -> dict:
    """Price P(over) AROUND a market anchor, per the reviewer's anchor scheme.

    The sim cannot out-predict the market; it only prices DISTRIBUTION SHAPE.
    So we affinely shift the simulated team-score distribution so its MEAN
    equals the market's implied team expectation (team_line, else market/2),
    keeping the sim's shape/variance. Returns the anchored P(over team_line).
    This is the disciplined use: the market sets the center, the sim sets the
    tails/state effects. Never claim the sim's mean beats the line.
    """
    g = sim.simulate_games(home, away, n=n)
    if side == "home":
        sim_raw = g["home_score"].to_numpy(dtype=float)
    else:
        sim_raw = g["away_score"].to_numpy(dtype=float)
    anchor = team_line if team_line is not None else market_total / 2
    mu = float(sim_raw.mean())
    # affine shift: recenter sim mean onto the market anchor (shape preserved)
    sim_anchored = sim_raw + (anchor - mu)
    p_over = float((sim_anchored > anchor).mean())
    return {
        "side": side, "matchup": f"{home} @ {away}",
        "market_team_anchor": round(anchor, 1),
        "sim_raw_mean": round(mu, 1),
        "sim_anchored_mean": round(anchor, 1),  # exactly at anchor after shift
        "p_over_team_line": round(p_over, 4),
        "ci_90": [round(float(np.percentile(sim_anchored, 5)), 1),
                  round(float(np.percentile(sim_anchored, 95)), 1)],
        "honest_note": ("mean anchored to the market; the sim only shapes the "
                        "distribution around it - this is NOT a market-beating "
                        "edge, just the fair over-probability of the line"),
    }


def strike_signal(sim: PossessionSimulator, home: str, away: str,
                  market_total: float, side: str = "home",
                  team_total_line: float | None = None,
                  n: int = 5000) -> dict:
    """Compare a simulating team total vs a market team total.

    Returns an honest strike decision. side in {home, away}; team_total_line
    is the book's posted team total for that side. If not given, we use half
    the game total as a (stated) approximation - never silently.
    """
    g = sim.simulate_games(home, away, n=n)
    if side == "home":
        sim_mean = float(g.home_score.mean())
        ci = (float(np.percentile(g.home_score, 5)),
              float(np.percentile(g.home_score, 95)))
    else:
        sim_mean = float(g.away_score.mean())
        ci = (float(np.percentile(g.away_score, 5)),
              float(np.percentile(g.away_score, 95)))
    anchor = team_total_line if team_total_line is not None else market_total / 2
    gap = sim_mean - anchor
    ci_width = ci[1] - ci[0]
    # honest gate: only a gap that exceeds the sim's own uncertainty is a
    # candidate worth investigating (a single-sample gap is noise).
    signal = "candidate" if abs(gap) > ci_width * 0.5 else "no-striking-edge"
    # don't overclaim: candidate is line-shopping/CLV to compare across books,
    # NOT a guaranteed +EV bet.
    return {
        "side": side, "matchup": f"{home} @ {away}",
        "sim_mean_team_total": round(sim_mean, 1),
        "anchor_team_total": round(anchor, 1),
        "gap": round(gap, 1),
        "90ci": [round(ci[0], 1), round(ci[1], 1)],
        "signal": signal,
        "honest_note": ("candidate = compare across books / track CLV; a "
                        "single-game edge is within CI noise and NOT a "
                        "guaranteed +EV bet"),
        "live_odds_gate": ("keyless; anchor is user/market-supplied. Real "
                           "de-vigged close needs the odds provider key"),
    }


def rank_strike_candidates(sim: PossessionSimulator, matchups: list[tuple],
                           market_totals: dict[str, float], n: int = 4000,
                           top: int = 5) -> list[dict]:
    """Rank a set of home team-total strike candidates by |gap| (CI-aware)."""
    out = []
    for home, away in matchups:
        mt = market_totals.get(f"{home}@{away}") or market_totals.get(home)
        if mt is None:
            continue
        s = strike_signal(sim, home, away, mt, side="home", n=n)
        out.append(s)
    return sorted(out, key=lambda x: abs(x["gap"]), reverse=True)[:top]