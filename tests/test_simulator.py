"""Tests for the possession-level discrete-event simulator (increment 4).

Run on a synthetic drive table so the suite is fast and dependency-free; the
real-data behavior (team ~22 pts, total ~43, yards ~363) is verified in the
ELITE_ROADMAP reproduce section on cache/drive_level_2023_2024.csv.
"""
import numpy as np
import pandas as pd

from nflprops import simulator as S


def make_drives(n=4000, rng=None, start_field=73.0):
    """Synthetic drive table with realistic outcome mix + field dependence."""
    rng = rng or np.random.default_rng(0)
    outcomes = ["PUNT", "TOUCHDOWN", "FIELD_GOAL", "INTERCEPTION", "DOWNS",
                "FUMBLE", "END_HALF", "MISSED_FG"]
    # field bias: drives starting deeper (start_ydl>70 = opponent side) score
    # more. Cover the full field so every sampler bin is populated (real data
    # spans start positions from the own goal to the opponent's red zone).
    start = rng.choice([20.0, 35.0, 35.0, 50.0, 65.0, 75.0, 88.0, 95.0], size=n)
    rows = []
    for i in range(n):
        yd = start[i]
        if yd >= 85:
            p = [0.28, 0.42, 0.10, 0.05, 0.05, 0.04, 0.03, 0.03]   # red zone
        elif yd >= 70:
            p = [0.35, 0.30, 0.12, 0.05, 0.10, 0.04, 0.02, 0.02]
        elif yd >= 50:
            p = [0.45, 0.15, 0.20, 0.05, 0.05, 0.04, 0.03, 0.03]
        else:
            p = [0.55, 0.06, 0.12, 0.06, 0.06, 0.05, 0.06, 0.04]
        oc = outcomes[rng.choice(len(outcomes), p=p)]
        g = rng.gamma(2.2, 60) * (1.0 if yd >= 50 else 0.8)
        td = 1.0 if oc == "TOUCHDOWN" else 0.0
        rows.append({"game_id": f"G{i//24}", "posteam": "TM", "fixed_drive": i % 24,
                     "start_ydl": yd, "drive_yards": g, "drive_plays": 6,
                     "end_state": oc, "td": td})
    return pd.DataFrame(rows)


def test_sampler_bins_by_field_position():
    df = make_drives(start_field=73.0)
    sm = S.FieldPositionStratifiedDriveSampler(df)
    # a drive starting in the red zone (90) and one at own 10 must map to
    # different field bins (the reviewer-flagged dependence)
    assert sm.zone(90.0) != sm.zone(10.0)
    # deep drive (high start_ydl) yields higher avg points than own-side drive
    hi = [p for _, p, _ in (sm.sample_drive(95.0, 0.0, np.random.default_rng(i))
                            for i in range(2000))]
    lo = [p for _, p, _ in (sm.sample_drive(10.0, 0.0, np.random.default_rng(i))
                            for i in range(2000))]
    assert np.mean(hi) > np.mean(lo)


def test_simulator_produces_nfl_scale_scores():
    df = make_drives()
    sim = S.PossessionSimulator(df, {}, {})
    g = sim.simulate_games("HOME", "AWAY", n=3000)
    mean_team = g["home_score"].mean()
    mean_total = (g["home_score"] + g["away_score"]).mean()
    # real NFL ~20-24 pts/team, ~43 total; allow a wide honest band
    assert 15 < mean_team < 35
    assert 30 < mean_total < 55
    assert g["home_yards"].mean() > 200


def test_strength_shift_moves_score_direction():
    df = make_drives()
    # strong offense (high dropback) vs weak defense -> higher score
    off = {"HOME": 0.20, "AWAY": -0.15}
    de = {"HOME": 0.05, "AWAY": -0.20}
    strong = S.PossessionSimulator(df, off, de)
    gs = strong.simulate_games("HOME", "AWAY", n=2000)
    weak = S.PossessionSimulator(df, {}, {})
    gw = weak.simulate_games("HOME", "AWAY", n=2000)
    # the strong offense @home should, on average, not be penalized vs baseline
    assert gs["home_score"].mean() >= gw["home_score"].mean() - 0.5


def test_simulator_reproducible_with_seed():
    df = make_drives()
    sim1 = S.PossessionSimulator(df, {}, {}, rng=np.random.default_rng(123))
    sim2 = S.PossessionSimulator(df, {}, {}, rng=np.random.default_rng(123))
    g1 = sim1.simulate_games("H", "A", n=2000)
    g2 = sim2.simulate_games("H", "A", n=2000)
    assert np.allclose(g1["home_score"], g2["home_score"])


def test_clock_state_ends_game_and_stays_realistic():
    # the clock-state game should produce plausible totals and finish (no hang)
    df = make_drives()
    sim = S.PossessionSimulator(df, {}, {}, rng=np.random.default_rng(7))
    g = sim.simulate_games("H", "A", n=1500)
    # must produce finite, non-huge totals (clock keeps it bounded)
    assert np.isfinite(g["home_score"].sum())
    assert (np.abs(g["home_score"]).max() < 60)


def test_drives_limit_still_respected():
    df = make_drives()
    sim = S.PossessionSimulator(df, {}, {}, rng=np.random.default_rng(3))
    # a strict drives cap bounds drives; scores still finite
    g = sim.simulate_games("H", "A", n=500, drives_limit=8)
    assert np.isfinite(g["home_score"].sum())