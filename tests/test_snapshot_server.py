"""Tests for the iOS backend snapshot server (honest keyless prop pricing)."""
import json

import pandas as pd

from ios.backend import snapshot_server as ss


def _small_stats(n=240, seed=0):
    import numpy as np
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(8):
        pid = f"P{i}"
        nm = f"WR{i}" if i < 6 else f"RB{i}"
        for g in range(n):
            # ~realistic receiving yards (gamma-ish) + some rushing rows
            rec = rng.gamma(2.0, 20.0)
            rush = rng.gamma(2.0, 15.0)
            pos = "WR" if i < 6 else "RB"
            rows.append({
                "player_id": pid,
                "player_display_name": nm,
                "position": pos,
                "season": 2023, "week": (g % 17) + 1,
                "receiving_yards": rec if i < 6 else 0.0,
                "rushing_yards": rush if i >= 6 else 0.0,
                "passing_yards": 0.0, "receptions": rec / 12,
                "passing_tds": 0, "rushing_tds": rush // 25, "receiving_tds": rec // 60,
            })
    return pd.DataFrame(rows)


def test_build_snapshot_prices_props():
    df = _small_stats()
    spec = []
    for idx in range(6):
        spec.append((f"WR{idx}", "receiving_yards", 60.0))
    snap = ss.build_snapshot(df, specs=spec, n=2000)
    assert snap["schema_version"] == "1.0"
    assert len(snap["props"]) > 0
    p = snap["props"][0]
    assert {"player", "p_over", "mean", "median", "ci_low", "ci_high",
            "edge", "kelly_stake"} <= set(p.keys())
    assert 0.0 <= p["p_over"] <= 1.0
    assert p["ci_low"] <= p["ci_high"]
    # honest framing present
    assert "honesty" in snap
    assert snap["honesty"]  # non-empty honest statement


def test_snapshot_skips_unresolved_player_silently():
    df = _small_stats()
    spec = [("NoSuchPlayer", "receiving_yards", 60.0),
            ("WR0", "receiving_yards", 60.0)]
    snap = ss.build_snapshot(df, specs=spec, n=2000)
    # unresolved player dropped, resolvable one kept
    names = [p["player"] for p in snap["props"]]
    assert "NoSuchPlayer" not in names
    assert "WR0" in names


def test_snapshot_signing_roundtrip():
    import hashlib
    import hmac
    body = json.dumps({"a": 1, "b": [2, 3]}, sort_keys=True).encode()
    secret = "test-secret"
    sig = ss._hmac_hex(body, secret)
    want = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert sig == want
    # wrong secret must NOT verify
    assert sig != hmac.new(b"wrong", body, hashlib.sha256).hexdigest()