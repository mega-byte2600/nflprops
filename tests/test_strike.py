"""Tests for the strike seam (increment 5): honest gap-vs-CI gate."""

from test_simulator import make_drives

from nflprops import simulator as S
from nflprops import strike as K


def _sim():
    df = make_drives()
    off = {"H": 0.2, "A": -0.1}
    de = {"H": 0.1, "A": -0.1}
    return S.PossessionSimulator(df, off, de), df


def test_strike_signal_refuses_no_market():
    sim, _ = _sim()
    s = K.strike_signal(sim, "H", "A", market_total=44.0, side="home", n=1000)
    assert s["signal"] in ("candidate", "no-striking-edge")
    assert s["sim_mean_team_total"] > 0
    assert s["honest_note"]  # honest caveat always present
    assert s["live_odds_gate"]  # gate always stated


def test_strike_model_mean_in_nfl_band():
    sim, _ = _sim()
    g = sim.simulate_games("H", "A", n=2000)
    mean_total = (g.home_score + g.away_score).mean()
    assert 30 < mean_total < 55


def test_candidate_flag_width_aware():
    sim, _ = _sim()
    # huge gap vs sim CI should be candidate; tiny gap not
    wide = K.strike_signal(sim, "H", "A", market_total=100.0, side="home", n=1500)
    assert wide["signal"] == "candidate"
    assert abs(wide["gap"]) > 10


def test_anchor_refuses_without_market():
    _, df = _sim()
    try:
        K.anchor_expected_total(df, "H", "A")
        assert False, "should have refused keyless"
    except ValueError:
        pass


def test_strike_uses_supplied_anchor():
    sim, _ = _sim()
    s = K.strike_signal(sim, "H", "A", market_total=44.0, side="away",
                        team_total_line=20.0, n=1000)
    assert s["anchor_team_total"] == 20.0


def test_anchored_over_probability_recenters_mean():
    sim, _ = _sim()
    res = K.anchored_over_probability(sim, "H", "A", market_total=44.0,
                                      side="home", team_line=22.0, n=2000)
    # after affine shift the anchored mean equals the market anchor
    assert res["sim_anchored_mean"] == 22.0
    assert 0.0 < res["p_over_team_line"] < 1.0
    assert res["honest_note"]  # honesty string present
    assert res["ci_90"][0] <= res["ci_90"][1]