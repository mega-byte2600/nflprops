"""Tests for nflprops. Builds a small synthetic DataFrame so tests run with
no 33MB download and quickly. The real-data behavior is covered by the
BML scripts in /docs (reproduce commands in the README)."""
import numpy as np
import pandas as pd

from nflprops import marginals as M
from nflprops import odds
from nflprops.copula import GaussianCopula, spearman_matrix
from nflprops.engine import Engine


def make_synthetic(seed=0):
    """Synthetic player-game data with realistic shapes. Jeff (WR): rec yd
    mean ~85; JT (RB): rush yd mean ~90. Used only for unit tests of the
    mechanics, not as evidence."""
    rng = np.random.default_rng(seed)
    rows = []
    players = {
        "P1": ("Justin Jeff", "WR", 55, 85.0, 20.0, 6.2),   # rec mean/sd/rec
        "P2": ("Jon Taylor", "RB", 25, 12.0, 9.0, 1.3),
        "P3": ("Tom Msiple", "QB", 275, 8.0, 4.0, 0.0),
    }
    n = 300
    for pid, (nm, pos, base, yds_mu, yds_sd, rec) in players.items():
        for g in range(n):
            recv = max(0, rng.normal(yds_mu, yds_sd))
            rush = max(0, rng.normal(base if pos != "RB" else 90, 20))
            rows.append({
                "player_id": pid, "player_display_name": nm, "position": pos,
                "season": 2019 + g % 5, "week": g % 17,
                "passing_yards": 0.0 if pos != "QB" else max(0, rng.normal(270, 60)),
                "rushing_yards": rush if g % 4 == 0 else 0.0,
                "receiving_yards": recv if g % 3 == 0 else 0.0,
                "receptions": float(np.random.default_rng(g).poisson(rec)) if g % 3 == 0 else 0.0,
                "passing_tds": 0.0, "rushing_tds": 0.0, "receiving_tds": 0.0,
            })
    return pd.DataFrame(rows)


DF = make_synthetic()


def test_american_conversion():
    assert abs(odds.american_to_prob(110) - 100/210) < 1e-9
    assert abs(odds.american_to_prob(-130) - 130/230) < 1e-9
    # round-trips
    for a in (110, -115, 200, -200, 300):
        assert abs(odds.prob_to_american(odds.american_to_prob(a)) - a) < 0.6


def test_kelly_worked_example():
    # +110 decimal 2.10, p=0.55 -> f=(1.1*0.55-0.45)/1.1 = 0.1409
    f = odds.kelly_fraction(0.55, 2.10)
    assert abs(f - 0.1409) < 1e-3


def test_fractional_kelly_stake():
    # 25% Kelly of 0.1409 on 10k ~ $352
    st = odds.fractional_kelly_stake(0.55, 2.10, 10000, fraction=0.25)
    assert abs(st - 0.25*0.1409*10000) < 5.0


def test_ev_and_edge():
    # P=0.6, decimal 2.0 -> EV 0.2, edge +0.1
    assert abs(odds.ev(0.6, 2.0) - 0.2) < 1e-9
    assert abs(odds.edge(0.6, 2.0) - 0.1) < 1e-9


def test_devig():
    d = odds.devig_proportional([0.55, 0.53])
    assert abs(sum(d) - 1.0) < 1e-9


def test_consensus_fair():
    # two books: Over/Under implied pairs with different vig -> fair Over median
    f = odds.consensus_fair([0.55, 0.54], [0.50, 0.47])
    # book1: 0.55/1.05=0.524 ; book2: 0.54/1.01=0.535 -> median ~0.529
    assert 0.52 <= f <= 0.54


def test_clv_signal():
    # your price +105 (higher implied) vs close +110 -> positive CLV if you beat close
    assert odds.clv_signal(2.05, 2.10) > 0  # your implied higher


def test_fit_player_gamma():
    fit = M.fit_player(DF, "P2", "rushing_yards", "gamma")
    assert fit is not None
    assert fit.family == "gamma_zinf"
    rvs = M.rvs(fit, 20000, rng=np.random.default_rng(1))
    assert rvs.min() >= 0
    assert rvs.mean() > 5  # P2 rushes regularly


def test_fit_player_dispersion_gated_nb():
    fit = M.fit_player(DF, "P1", "receptions", "dispersion-gated-nb")
    assert fit is not None
    rvs = M.rvs(fit, 20000, rng=np.random.default_rng(2))
    assert rvs.dtype.kind in "fi"
    assert rvs.min() >= 0


def test_over_prob():
    fit = M.fit_player(DF, "P3", "passing_yards", "normal")
    assert fit is not None
    p = M.over_prob(fit, 250)
    assert 0.0 < p < 1.0


def test_copula_matrix_square():
    R = spearman_matrix(DF)
    assert R.shape == (7, 7)
    assert np.allclose(R, R.T)


def test_copula_correlates():
    # build a copula where two stats are correlated and check samples track it.
    # NOTE: heavy zero-inflation places an independent (0,0) mass that lowers the
    # realized correlation vs the copula target (a documented, honest dilution);
    # so assert the correlation among JOINTLY-ACTIVE samples, which is where the
    # copula's dependence actually lives.
    R = np.eye(7)
    R[2, 3] = R[3, 2] = 0.8   # receiving_yds <-> receptions
    cop = GaussianCopula(R)
    fit_for = lambda pid, stat: M.fit_player(DF, "P1", stat,
                                             "gamma" if stat == "receiving_yards"
                                             else "dispersion-gated-nb")
    out = cop.sample(fit_for, "P1", n=20000, rng=np.random.default_rng(3))
    x = out["receiving_yards"]; y = out["receptions"]
    both = (x > 0) & (y > 0)
    r = float(np.corrcoef(x[both], y[both])[0, 1]) if both.sum() > 50 else 0.0
    assert r > 0.3  # positively correlated on the active path


def test_engine_forecast():
    eng = Engine(DF, seed=42)
    fc = eng.forecast("P1", "receiving_yards", 80, n=5000)
    assert fc is not None
    assert 0.0 < fc.p_over < 1.0
    assert fc.ci90[0] <= fc.ci90[1]


def test_calibration_pit_runs():
    from nflprops.calibration import pit_backtest
    train = DF[DF.season < 2022]
    test = DF[DF.season >= 2022]
    res = pit_backtest(train, test, (("receiving_yards", "gamma"),))
    assert len(res) >= 1