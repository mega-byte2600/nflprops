"""Free, keyless data sources (CarpeDATA): a registry and one resilient fetcher.

Every source here is public and needs no key. Fetching follows the CarpeDATA rules
(.claude/skills/carpedata/SKILL.md):
- a timeout on every call; bounded retry with exponential backoff and jitter on transport
  errors and 5xx ONLY; 403 and 429 stop immediately and are reported, never routed around;
- a schema check (required columns) before a file replaces the cached copy;
- an append-only manifest entry per fetch (source, url, status, bytes, sha256, as-of);
- fallback = the last-known-good cached file, labelled stale with its age. Never synthetic.

The transport is injectable, so tests run with the network disabled.
"""
from __future__ import annotations

import hashlib
import io
import json
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

Transport = Callable[[str, float], "tuple[int, bytes]"]
RETRYABLE = frozenset({0, 500, 502, 503, 504})
RELEASES = "https://github.com/nflverse/nflverse-data/releases/download/"


@dataclass(frozen=True)
class Source:
    key: str
    url: str
    licence: str
    required: tuple[str, ...]
    note: str


REGISTRY: dict[str, Source] = {
    "player_stats_legacy": Source(
        "player_stats_legacy", RELEASES + "player_stats/player_stats.csv.gz", "CC-BY-4.0",
        ("player_id", "season", "week", "recent_team"),
        "Weekly player box stats 1999-2024 (nflverse froze this file after 2024)."),
    "stats_player_week": Source(
        "stats_player_week", RELEASES + "stats_player/stats_player_week_{season}.csv",
        "CC-BY-4.0", ("player_id", "season", "week", "team"),
        "Weekly player box stats 2025+ (current season, updated in-season)."),
    "schedules": Source(
        "schedules", "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv",
        "CC-BY-4.0", ("game_id", "season", "week", "home_team", "away_team",
                      "spread_line", "total_line"),
        "Schedules and results with CLOSING spread and total (free market anchor)."),
    "snap_counts": Source(
        "snap_counts", RELEASES + "snap_counts/snap_counts_{season}.csv", "CC-BY-4.0",
        ("game_id", "player", "offense_pct"), "Offensive snap share per player-game (PFR)."),
    "injuries": Source(
        "injuries", RELEASES + "injuries/injuries_{season}.csv", "CC-BY-4.0",
        ("season", "week", "gsis_id", "report_status"), "Official weekly injury reports."),
    "depth_charts": Source(
        "depth_charts", RELEASES + "depth_charts/depth_charts_{season}.csv", "CC-BY-4.0",
        ("dt", "team", "gsis_id", "pos_abb", "pos_rank"),
        "Depth-chart snapshots (role / usage prior). Schema drift caught 2026-11-27: from "
        "2026 nflverse publishes timestamped snapshots (dt) instead of season/week rows."),
}


def _urllib_transport(url: str, timeout: float) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "nflprops/0.2 (+keyless research)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:  # noqa: BLE001 - transport failure is status 0, reported
        return 0, str(e).encode()


def fetch(url: str, transport: Transport = _urllib_transport, timeout: float = 60.0,
          attempts: int = 3, base_delay: float = 1.0,
          sleep: Callable[[float], None] = time.sleep) -> tuple[int, bytes]:
    """GET with bounded retry on transport/5xx only. 403/429 return at once."""
    status, body = transport(url, timeout)
    for i in range(1, attempts):
        if status not in RETRYABLE:
            break
        sleep(base_delay * (2 ** (i - 1)) * (1 + random.random()))
        status, body = transport(url, timeout)
    return status, body


def _manifest(cache: Path, row: dict) -> None:
    with (cache / "manifest.jsonl").open("a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")


def get(key: str, cache: Path, season: int | None = None, refresh: bool = False,
        transport: Transport = _urllib_transport) -> tuple[pd.DataFrame, dict]:
    """Return (frame, status) for a registered source, cached under `cache`.

    status = {"state": FRESH|CACHED|STALE|UNAVAILABLE, "as_of": iso, "reason": str}.
    STALE means the live fetch failed and the last-known-good file is served.
    """
    src = REGISTRY[key]
    url = src.url.format(season=season) if season is not None else src.url
    cache.mkdir(parents=True, exist_ok=True)
    name = f"{key}{'_' + str(season) if season is not None else ''}.csv"
    path = cache / name
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if path.exists() and not refresh:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        return _read(path), {"state": "CACHED", "as_of": mtime.isoformat(timespec="seconds"),
                             "reason": ""}
    status, body = fetch(url, transport)
    reason = ""
    if status == 200 and body:
        raw = _gunzip(body) if url.endswith(".gz") else body
        try:
            df = pd.read_csv(io.BytesIO(raw), low_memory=False)
            missing = [c for c in src.required if c not in df.columns]
            reason = f"SCHEMA_MISSING:{','.join(missing)}" if missing else ""
        except Exception as e:  # noqa: BLE001
            df, reason = None, f"PAYLOAD_MALFORMED:{type(e).__name__}"
        if not reason and df is not None and len(df):
            path.write_bytes(raw)
            _manifest(cache, {"source": key, "url": url, "status": 200, "bytes": len(raw),
                              "sha256": hashlib.sha256(raw).hexdigest(), "rows": len(df),
                              "fetched_at": now, "state": "FRESH"})
            return df, {"state": "FRESH", "as_of": now, "reason": ""}
        reason = reason or "EMPTY_PAYLOAD"
    else:
        reason = {403: "HTTP_403_STOP", 429: "HTTP_429_STOP"}.get(status, f"HTTP_{status}")
    _manifest(cache, {"source": key, "url": url, "status": status, "fetched_at": now,
                      "state": "FAILED", "reason": reason})
    if path.exists():
        mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        return _read(path), {"state": "STALE", "as_of": mtime.isoformat(timespec="seconds"),
                             "reason": reason}
    return pd.DataFrame(), {"state": "UNAVAILABLE", "as_of": None, "reason": reason}


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _gunzip(b: bytes) -> bytes:
    import gzip
    return gzip.decompress(b)


def player_weeks(legacy: pd.DataFrame, current: list[pd.DataFrame]) -> pd.DataFrame:
    """One weekly player table across the legacy (<=2024) and current (2025+) releases.

    The current release names the team column `team`; the legacy one `recent_team`. Rows are
    de-duplicated on (player_id, season, week, season_type), the current release winning.
    """
    frames = [legacy.assign(_src=0)]
    for c in current:
        if len(c):
            frames.append(c.rename(columns={"team": "recent_team"}).assign(_src=1))
    df = pd.concat(frames, ignore_index=True, sort=False)
    keys = [k for k in ("player_id", "season", "week", "season_type") if k in df.columns]
    df = df.sort_values("_src").drop_duplicates(keys, keep="last").drop(columns="_src")
    return df.sort_values(["season", "week"]).reset_index(drop=True)


def implied_team_totals(games: pd.DataFrame) -> pd.DataFrame:
    """Closing-market implied points per team-game: (total +/- spread) / 2.

    nflverse convention, verified 2026-11-27 on 7,442 games: spread_line > 0 means the HOME
    team is favoured (corr with home margin +0.43, mean residual +0.06 pts).
    """
    g = games.dropna(subset=["spread_line", "total_line"])
    home = pd.DataFrame({"season": g.season, "week": g.week, "team": g.home_team,
                         "implied": (g.total_line + g.spread_line) / 2})
    away = pd.DataFrame({"season": g.season, "week": g.week, "team": g.away_team,
                         "implied": (g.total_line - g.spread_line) / 2})
    return pd.concat([home, away], ignore_index=True)
