"""Snapshot server for the NFL prop decision app.

The iPhone app does NOT hold an odds key or do heavy compute. This script runs
the honest engine (per-player marginals + Gaussian copula + Monte Carlo with
95% CI) server-side, and writes a SIGNED, static JSON snapshot the iOS app
reads. That is the dkori-protect architecture: batch precompute once, serve a
signed snapshot, no API key in the client (standing secrets rule).

Keyless-first: it prices from nflverse box statistics (cache/player_stats.csv)
already on disk. Live multi-book odds hydration is a documented next step
(gated on the user's provider key) - until then, odds fields are None and the
engine honestly reports it cannot compute a de-vigged fair price.

VERIFIED = runs on real data and produces a well-formed, schema-checked,
self-authenticating snapshot (see docs/ELITE_ROADMAP or tests). Does NOT claim
a money edge - it reports distribution + CI and defers to the sharp anchor.

Usage:
  venv/bin/python ios/backend/snapshot_server.py --stats cache/player_stats.csv \
      --out ios/backend/props_snapshot.json --sign-secret "$SNITCH_SECRET"

The signature uses HMAC-SHA256 over the JSON body with a shared secret the
server and app both hold; it proves body integrity (not authenticity of a
third party). Never log or commit the secret.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone

from nflprops import Engine
from nflprops import data as d


def _hmac_hex(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


DEFAULT_SPECS = [
    ("Justin Jefferson", "receiving_yards", 70.5),
    ("Tyreek Hill", "receiving_yards", 70.5),
    ("Derrick Henry", "rushing_yards", 55.5),
    ("Patrick Mahomes", "passing_yards", 275.5),
    ("A.J. Brown", "receiving_yards", 65.5),
]


def build_snapshot(stats_df, specs=DEFAULT_SPECS, n: int = 20000,
                   ci: float = 0.95) -> dict:
    """Price a set of canonical (player, stat, line) props; return the snapshot."""
    eng = Engine(stats_df)
    props = []
    for pname, stat, line in specs:
        try:
            pid = d.resolve_player(stats_df, pname, stat)
        except KeyError:
            continue  # no usage data for this name/stat; skip honestly
        fc = eng.forecast(pid, stat, line, n=n, ci_level=ci)
        if fc is None:
            continue
        lo, hi = fc.ci
        props.append({
            "player": pname, "stat": stat, "line": line,
            "p_over": round(float(fc.p_over), 4),
            "mean": round(float(fc.mean), 1),
            "median": round(float(fc.median), 1),
            "ci_low": round(float(lo), 1),
            "ci_high": round(float(hi), 1),
            "ci_level": ci,
            # honest: no de-vigged fair price until an odds provider is wired
            "fair_price_honest_note": ("no live odds wired yet (keyless); "
                                       "p_over is model distribution, not "
                                       "a market fair price"),
            "edge": None, "kelly_stake": None,
        })
    return {
        "schema_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "engine": {"ci_default": ci, "n_monte_carlo": n},
        "honesty": ("distributions + CI only; no guaranteed winners; "
                    "judged by CLV/calibration over many bets, not short-run ROI"),
        "props": props,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sign-secret", default=os.environ.get("SNITCH_SECRET", ""))
    ap.add_argument("--ci", type=float, default=0.95)
    ap.add_argument("--n", type=int, default=20000)
    args = ap.parse_args()

    from nflprops import load_stats
    df = load_stats(args.stats)
    snap = build_snapshot(df, n=args.n, ci=args.ci)
    body = json.dumps(snap, sort_keys=True).encode()
    sig = _hmac_hex(body, args.sign_secret) if args.sign_secret else None
    out = {"signature": sig, "payload": snap}
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {args.out}: {len(snap['props'])} props "
          f"{'(signed)' if sig else '(UNSIGNED - set --sign-secret)'}")


if __name__ == "__main__":
    main()