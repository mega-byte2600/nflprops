"""Hermetic tests for the CarpeDATA source layer and projection v2 (no network)."""
import numpy as np
import pandas as pd

from nflprops import projection as P
from nflprops import sources as S

CSV = b"player_id,season,week,team\np1,2026,1,KC\n"


def _transport(seq):
    calls = []

    def t(url, timeout):
        calls.append(url)
        return seq[min(len(calls) - 1, len(seq) - 1)]
    return t, calls


def test_403_and_429_stop_immediately():
    for code in (403, 429):
        t, calls = _transport([(code, b"")])
        status, _ = S.fetch("u", t, sleep=lambda s: None)
        assert status == code and len(calls) == 1


def test_5xx_retries_bounded_then_succeeds():
    t, calls = _transport([(503, b""), (0, b"reset"), (200, CSV)])
    status, body = S.fetch("u", t, attempts=3, sleep=lambda s: None)
    assert status == 200 and body == CSV and len(calls) == 3


def test_get_validates_schema_writes_manifest_and_serves_stale(tmp_path):
    t, _ = _transport([(200, CSV)])
    df, st = S.get("stats_player_week", tmp_path, season=2026, refresh=True, transport=t)
    assert st["state"] == "FRESH" and len(df) == 1
    assert (tmp_path / "manifest.jsonl").read_text().count('"FRESH"') == 1
    t2, _ = _transport([(403, b"")])
    df2, st2 = S.get("stats_player_week", tmp_path, season=2026, refresh=True, transport=t2)
    assert st2["state"] == "STALE" and st2["reason"] == "HTTP_403_STOP" and len(df2) == 1


def test_get_rejects_payload_missing_required_columns(tmp_path):
    t, _ = _transport([(200, b"a,b\n1,2\n")])
    _df, st = S.get("stats_player_week", tmp_path, season=2026, refresh=True, transport=t)
    assert st["state"] == "UNAVAILABLE" and st["reason"].startswith("SCHEMA_MISSING")
    assert not (tmp_path / "stats_player_week_2026.csv").exists()


def test_implied_totals_follow_nflverse_sign_convention():
    g = pd.DataFrame({"season": [2026], "week": [1], "home_team": ["KC"], "away_team": ["LV"],
                      "spread_line": [7.0], "total_line": [47.0]})
    it = S.implied_team_totals(g).set_index("team").implied
    assert it["KC"] == 27.0 and it["LV"] == 20.0


def _synthetic(n_players=40, games=40, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(n_players):
        lam = rng.uniform(0.1, 0.8)
        for gi in range(games):
            rows.append({"player_id": f"p{p}", "position": "RB", "season": 2015 + gi // 17,
                         "week": gi % 17 + 1, "team": "KC", "implied": 22.0,
                         "y": float(rng.poisson(lam))})
    return pd.DataFrame(rows)


def test_features_use_prior_games_only():
    f = _synthetic()
    a = P.features(f, 8.0, td=True)
    f2 = f.copy()
    f2.loc[f2.index[-1], "y"] = 99.0          # change the LAST game's outcome only
    b = P.features(f2, 8.0, td=True)
    cols = ["ew_y", "ew_a", "line_med", "base"]
    pd.testing.assert_frame_equal(a[cols].iloc[[-1]], b[cols].iloc[[-1]])


def test_td_probability_is_near_truth_on_synthetic_poisson():
    f = P.features(_synthetic(80, 60, seed=1), 16.0, td=True)
    loc = P.location(f, "rushing_tds", P.Params(h=16.0, k=2.0, beta=0.0))
    p = P.p_over(loc, "rushing_tds", float("nan"), nu=32.0)
    assert abs(p.mean() - (loc.y > 0.5).mean()) < 0.03


def test_effective_sample_size_is_exact_kish():
    f = P.features(_synthetic(1, 30), 8.0, td=True)
    r = 0.5 ** (1 / 8.0)
    n = 23
    w = r ** np.arange(n)
    assert abs(f.n_eff.iloc[n] - w.sum() ** 2 / (w ** 2).sum()) < 1e-9
