"""CarpeDATA health check: one fetch per registered free source, a table of states.

    python scripts/check_sources.py [--cache cache] [--season 2026] [--json]

Keyless public sources only, one request each (no polling loops). 403/429 are reported
and not retried. A failed fetch serves the last-known-good cached file labelled STALE.
Exit 0 when every source is FRESH or CACHED; 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from nflprops import sources as S

PER_SEASON = {"stats_player_week", "snap_counts", "injuries", "depth_charts"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="cache")
    ap.add_argument("--season", type=int, default=date.today().year)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rows = []
    for key, src in S.REGISTRY.items():
        if key == "player_stats_legacy":
            continue  # frozen at 2024 by nflverse; refreshed only on demand
        season = a.season if key in PER_SEASON else None
        df, st = S.get(key, Path(a.cache), season=season, refresh=True)
        latest = ""
        if len(df) and "week" in df.columns and "season" in df.columns:
            s = df[df.season == df.season.max()]
            latest = f"{int(s.season.max())} wk {int(s.week.max())}"
        rows.append({"source": key, "season": season, "state": st["state"],
                     "rows": len(df), "latest": latest, "as_of": st["as_of"],
                     "reason": st["reason"], "licence": src.licence})
    if a.json:
        print(json.dumps(rows, indent=1))
    else:
        print("| source | state | rows | latest | as-of | reason |\n|---|---|---|---|---|---|")
        for r in rows:
            print(f"| {r['source']} | {r['state']} | {r['rows']:,} | {r['latest']} | "
                  f"{r['as_of']} | {r['reason']} |")
    return 0 if all(r["state"] in ("FRESH", "CACHED") for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
