"""Data layer: keyless nflverse player-season statistics.

The package runs entirely on nflverse's free, CC-BY-4.0 player_stats.csv
(1999-present), which carries every stat a prop line touches: passing/rushing/
receiving yards, receptions, targets, TDs, target_share, EPA/WOPR, fantasy
points. No API key required - this is the keyless foundation of the engine.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Standard keyless download URL (re-verified Nov 2026).
NFLVERSE_PLAYER_STATS = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "player_stats/player_stats.csv.gz"
)

# Stats the engine models, mapped to their distribution family (MEASURED via
# the BML loop on real nflverse data - see docs/BML_LOOP.md):
#   rushing/receiving yards -> gamma (right-skew, skew ~+1.7)
#   passing yards          -> normal (mildly LEFT-skew, -0.18)
#   TDs / receptions       -> count families (see marginals.py)
STAT_FAMILY = {
    "passing_yards": "normal",
    "rushing_yards": "gamma",
    "receiving_yards": "gamma",
    "passing_tds": "poisson",
    "rushing_tds": "poisson",
    "receiving_tds": "poisson",
    "receptions": "dispersion-gated-nb",  # NB if overdispersed, else Poisson
}


def ensure_cache(cache_dir: Path, redownload: bool = False) -> Path:
    """Return the cached CSV path, downloading keyless if absent.

    Writes to <cache_dir>/player_stats.csv. No auth, no key, forever free.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    csv_path = cache_dir / "player_stats.csv"
    if csv_path.exists() and not redownload:
        return csv_path
    import gzip
    import shutil
    import urllib.request

    gz_path = cache_dir / "player_stats.csv.gz"
    print(f"[nflprops] downloading nflverse player stats -> {gz_path.name}")
    urllib.request.urlretrieve(NFLVERSE_PLAYER_STATS, gz_path)
    with gzip.open(gz_path, "rb") as f_in, open(csv_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    gz_path.unlink(missing_ok=True)
    return csv_path


def load_stats(data_source: str | Path | pd.DataFrame, min_season: int = 2003) -> pd.DataFrame:
    """Load player stats from a path (or accept a DataFrame), optional season filter."""
    if isinstance(data_source, pd.DataFrame):
        df = data_source
    else:
        fp = Path(data_source)
        if not fp.exists():
            raise FileNotFoundError(f"nflverse stats not found: {fp}")
        df = pd.read_csv(fp)
    if "season" in df.columns and min_season:
        df = df[df["season"] >= min_season]
    return df.reset_index(drop=True)


def get_names(df: pd.DataFrame) -> dict[str, str]:
    """player_id -> display name map."""
    sub = df.dropna(subset=["player_id", "player_display_name"])
    return dict(zip(sub["player_id"], sub["player_display_name"]))


def available_players(df: pd.DataFrame, stat: str, min_games: int = 8) -> pd.Series:
    """Players with at least min_games of non-null usage in a stat."""
    g = df[df[stat].notna()].groupby("player_id")[stat]
    return g.agg(lambda s: (s > 0).sum() >= min_games)


def resolve_player(df: pd.DataFrame, name: str, stat: str | None = None) -> str:
    """Resolve a display name (possibly partial) to a player_id.

    Disambiguates same-name players by preferring the one with the most
    positive-usage rows in the requested stat (e.g. Justin Jefferson over
    retired Shawn Jefferson for receiving), else most total games. Raises
    KeyError if no player matches. Shared by the CLI and the snapshot server.
    """
    names = get_names(df)
    hits = [pid for pid, nm in names.items() if name.lower() in str(nm).lower()]
    if not hits:
        raise KeyError(
            f"no player matching '{name}' (in data only if they had usage)")
    if len(hits) == 1:
        return str(hits[0])
    if stat is not None:
        sub = df[df["player_id"].isin(hits) & df[stat].notna()]
        if not sub.empty:
            vol = sub.groupby("player_id")[stat].apply(lambda s: (s > 0).sum())
            if len(vol):
                return str(vol.sort_values(ascending=False).index[0])
    g = df[df["player_id"].isin(hits)].groupby("player_id").size()
    return str(g.sort_values(ascending=False).index[0])