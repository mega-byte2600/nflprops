"""Projection v2: one-step-ahead, recency-weighted, shrunk, market-anchored prop probabilities.

Method (ADR-0003; every choice is tuned on validation seasons only and tested later):
1. One-step-ahead: each player-game is predicted only from that player's PRIOR games
   (Hyndman & Athanasopoulos, FPP3 s5.10, rolling origin).
2. Recency: exponentially weighted moments with half-life h games. With decay r = 0.5^(1/h)
   the Kish effective sample size of n prior games is (1-r^n)(1+r) / ((1-r)(1+r^n)).
3. Empirical-Bayes shrinkage toward the position mean: m* = (n_eff*m + k*m_pos)/(n_eff + k)
   (Efron & Morris 1975; Gelman et al., BDA3 ch.5). Applied to the active-game mean and to
   P(active).
4. Market anchor: the mean scales by (implied_t / ew_implied)^beta, where implied_t is this
   game's closing-line implied team total and ew_implied the same EW average over the
   player's prior games, i.e. it adjusts for this week's game environment versus the one the
   player's history was produced in.
5. Predictive distribution. Yards: zero with prob 1-pi, else Gamma with the mean above and a
   shape from the out-of-sample dispersion of y/mean on validation data, so parameter
   uncertainty is inside the predictive spread. Passing yards: Normal with sd = c*mean.
   TDs: Poisson-gamma (negative binomial) with lambda from step 2-4 and mixing shape nu,
   P(Y >= 1) = 1 - (1 + lambda/nu)^(-nu). No double zero-inflation.
6. Platt recalibration (logistic on logit p) fit on validation seasons, applied to test.

Evaluation lines are book-style: TDs 0.5; yards floor(median of the prior 8 games) + 0.5.
The naive baseline is the Laplace-smoothed hit rate at that line over the prior 16 games.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats as st
from scipy.special import expit, logit

YARDS = ("passing_yards", "rushing_yards", "receiving_yards")
TDS = ("rushing_tds", "receiving_tds")
STATS = YARDS + TDS
MIN_PRIOR = 8
MIN_LINE = {"passing_yards": 150.5, "rushing_yards": 20.5, "receiving_yards": 20.5}
POS = {"passing_yards": ("QB",), "rushing_yards": ("RB", "QB"),
       "receiving_yards": ("WR", "TE", "RB"), "rushing_tds": ("RB", "QB"),
       "receiving_tds": ("WR", "TE", "RB")}


@dataclass(frozen=True)
class Params:
    h: float = 8.0       # recency half-life in games
    k: float = 5.0       # shrinkage strength (pseudo-games of the position prior)
    beta: float = 0.5    # market-anchor elasticity


def frame(weeks: pd.DataFrame, implied: pd.DataFrame, stat: str) -> pd.DataFrame:
    """Regular-season player-games for one stat with this game's implied team total."""
    w = weeks[(weeks.get("season_type", "REG") == "REG") & weeks[stat].notna()]
    w = w[w["position"].isin(POS[stat])]
    f = w[["player_id", "position", "season", "week", "recent_team", stat]].rename(
        columns={stat: "y", "recent_team": "team"})
    f = f.merge(implied, on=["season", "week", "team"], how="left")
    f["y"] = f["y"].astype(float).clip(lower=0)
    return f.sort_values(["player_id", "season", "week"]).reset_index(drop=True)


def _prior_ewm(g: pd.core.groupby.SeriesGroupBy, h: float) -> pd.Series:
    return g.transform(lambda s: s.shift(1).ewm(halflife=h, min_periods=1).mean())


def features(f: pd.DataFrame, h: float, td: bool) -> pd.DataFrame:
    """Prior-only features for each player-game (no information from the game itself)."""
    f = f.reset_index(drop=True).copy()
    gp = f.groupby("player_id")
    f["n_prior"] = gp.cumcount()
    f["a"] = (f.y > 0).astype(float)
    f["ew_y"] = _prior_ewm(gp["y"], h)
    f["ew_a"] = _prior_ewm(gp["a"], h)
    f["ew_imp"] = _prior_ewm(gp["implied"], h)
    r = 0.5 ** (1.0 / h)
    rn = r ** f.n_prior.to_numpy(dtype=float)
    # Kish effective n of weights r^0..r^(n-1): (1-r^n)(1+r) / ((1-r)(1+r^n))
    f["n_eff"] = (1 - rn) * (1 + r) / ((1 - r) * (1 + rn))
    f["line_med"] = gp["y"].transform(lambda s: s.shift(1).rolling(8, min_periods=8).median())
    f["line"] = np.where(td, 0.5, np.floor(f.line_med) + 0.5)
    f["base"] = _baseline(f)
    f["ew_hit"] = _ew_hit(f, h)
    return f


def _ew_hit(f: pd.DataFrame, h: float) -> np.ndarray:
    """Recency-weighted (half-life h) hit rate at this game's line over ALL prior games,
    Laplace-smoothed: (sum w*hit + 1) / (sum w + 2). Prior games only."""
    out = np.empty(len(f))
    r = 0.5 ** (1.0 / h)
    y_all, line_all = f.y.to_numpy(), f.line.to_numpy()
    for pos in f.groupby("player_id").indices.values():
        y, ln = y_all[pos], line_all[pos]
        res = np.empty(len(pos))
        for j in range(len(pos)):
            if j == 0:
                res[j] = 0.5
                continue
            w = r ** np.arange(j - 1, -1, -1)            # most recent prior game weight 1
            res[j] = ((w * (y[:j] > ln[j])).sum() + 1.0) / (w.sum() + 2.0)
        out[pos] = res
    return out


def _baseline(f: pd.DataFrame) -> np.ndarray:
    """Laplace-smoothed hit rate at this game's line over the player's prior 16 games."""
    out = np.empty(len(f))
    y_all, line_all = f.y.to_numpy(), f.line.to_numpy()
    for pos in f.groupby("player_id").indices.values():      # positional, already sorted
        y, ln = y_all[pos], line_all[pos]
        res = np.empty(len(pos))
        for j in range(len(pos)):
            prev = y[max(0, j - 16):j]
            res[j] = ((prev > ln[j]).sum() + 1.0) / (len(prev) + 2.0)
        out[pos] = res
    return out


def _position_prior(f: pd.DataFrame) -> pd.DataFrame:
    """Previous season's position means (active-game mean, P(active), all-game mean)."""
    act = f[f.y > 0].groupby(["season", "position"]).y.mean().rename("pos_m")
    pa = f.groupby(["season", "position"]).a.mean().rename("pos_a")
    pm = f.groupby(["season", "position"]).y.mean().rename("pos_all")
    p = pd.concat([act, pa, pm], axis=1).reset_index()
    p["season"] = p["season"] + 1               # strictly the PREVIOUS season
    return p


def location(f: pd.DataFrame, stat: str, prm: Params) -> pd.DataFrame:
    """Shrunk, market-anchored predictive location for each eligible player-game."""
    f = f.merge(_position_prior(f), on=["season", "position"], how="left")
    f = f[(f.n_prior >= MIN_PRIOR) & f.pos_m.notna() & f.ew_y.notna()].copy()
    ne, k = f.n_eff, prm.k
    anchor = np.where(f.implied.notna() & f.ew_imp.notna() & (f.ew_imp > 0),
                      (f.implied / f.ew_imp) ** prm.beta, 1.0)
    if stat in TDS:
        f["lam"] = (ne * f.ew_y + k * f.pos_all) / (ne + k) * anchor
    else:
        m_act = np.where(f.ew_a > 0, f.ew_y / f.ew_a.where(f.ew_a > 0, 1), f.pos_m)
        f["mu"] = (ne * m_act + k * f.pos_m) / (ne + k) * anchor
        f["pi"] = ((ne * f.ew_a + k * f.pos_a) / (ne + k)).clip(1e-3, 1 - 1e-3)
        f = f[f.line >= MIN_LINE[stat]]
    return f


def dispersion(loc: pd.DataFrame, stat: str) -> float:
    """Out-of-sample dispersion: gamma shape 1/var(y/mu) (yards) or c = sd(y/mu) (passing)."""
    if stat in TDS:
        return float("nan")
    act = loc[loc.y > 0]
    ratio = (act.y / act.mu).replace([np.inf, -np.inf], np.nan).dropna()
    ratio = ratio.clip(upper=ratio.quantile(0.999))
    return float(ratio.std()) if stat == "passing_yards" else float(1.0 / ratio.var())


def p_over(loc: pd.DataFrame, stat: str, disp: float, nu: float = 4.0) -> np.ndarray:
    if stat in TDS:
        lam = loc.lam.to_numpy().clip(1e-6)
        return 1.0 - (1.0 + lam / nu) ** (-nu)
    mu, line = loc.mu.to_numpy(), loc.line.to_numpy()
    if stat == "passing_yards":
        tail = st.norm.sf(line, mu, disp * mu)
    else:
        tail = st.gamma.sf(line, disp, 0, mu / disp)
    return loc.pi.to_numpy() * tail


class Platt:
    """Logistic recalibration p' = expit(a + b*logit(p)), fit by maximum likelihood."""

    def __init__(self, p: np.ndarray, y: np.ndarray) -> None:
        from scipy.optimize import minimize
        x = logit(np.clip(p, 1e-4, 1 - 1e-4))

        def nll(w):
            q = np.clip(expit(w[0] + w[1] * x), 1e-9, 1 - 1e-9)
            return -np.mean(y * np.log(q) + (1 - y) * np.log(1 - q))

        self.a, self.b = minimize(nll, np.array([0.0, 1.0]), method="Nelder-Mead").x

    def __call__(self, p: np.ndarray) -> np.ndarray:
        return expit(self.a + self.b * logit(np.clip(p, 1e-4, 1 - 1e-4)))


class Logistic:
    """Plain logistic regression by maximum likelihood (used for the stacked baseline)."""

    def __init__(self, X: np.ndarray, y: np.ndarray) -> None:
        from scipy.optimize import minimize
        Xc = np.column_stack([np.ones(len(X)), X])

        def nll(w):
            z = Xc @ w
            return float(np.mean(np.logaddexp(0, z) - y * z))

        self.w = minimize(nll, np.zeros(Xc.shape[1]), method="L-BFGS-B").x

    def __call__(self, X: np.ndarray) -> np.ndarray:
        return expit(np.column_stack([np.ones(len(X)), X]) @ self.w)


def stacked_features(loc: pd.DataFrame) -> np.ndarray:
    """Baseline inputs: logit(recency-weighted prior hit rate), log anchor ratio, log implied
    total, log n. Uses the EW hit rate (not the last-16 rate) so the baseline is hard to beat."""
    imp = loc.implied.fillna(22.0).clip(lower=1)
    ratio = (loc.implied / loc.ew_imp).replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(0.2, 5)
    return np.column_stack([logit(np.clip(loc.ew_hit, 1e-3, 1 - 1e-3)), np.log(ratio),
                            np.log(imp), np.log1p(loc.n_prior)])


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))
