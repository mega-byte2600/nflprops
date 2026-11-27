# Data sources registry (CarpeDATA)

The source of truth in code is `src/nflprops/sources.py` (`REGISTRY`). Health:
`python scripts/check_sources.py` (one request per source; 403 and 429 are reported and
never retried; on a failure the last-known-good cached file is served labelled STALE).

## Wired: free and keyless (health checked 2026-11-27, all FRESH)
| Source | What | Coverage | Used by | Licence |
|---|---|---|---|---|
| `player_stats_legacy` | Weekly player box stats | 1999–2024 (frozen by nflverse) | v1 engine, v2 history | CC-BY-4.0 |
| `stats_player_week` | Weekly player box stats | **2025–2026 wk 12** (in-season) | v2 (current season) | CC-BY-4.0 |
| `schedules` (nfldata `games.csv`) | Results with **closing spread and total** | 1999–2026, lines 100% for 2003–2024 | v2 market anchor (implied team total) | CC-BY-4.0 |
| `snap_counts` | Offensive snap share per player-game | 2012–2026 | next: usage prior (S6) | CC-BY-4.0 (PFR-derived) |
| `injuries` | Official weekly injury reports | 2009–2026 | next: availability (S7) | CC-BY-4.0 |
| `depth_charts` | Depth-chart snapshots | 2001–2026 (snapshot format from 2026) | next: role prior | CC-BY-4.0 |

**Gaps closed 2026-11-27.** The engine had been reading a file nflverse froze after 2024
(it moved weekly stats to `stats_player`), so 2025–26 was missing. Closing lines (free)
were not used at all. They are now the v2 market anchor.

## Candidates (free; not wired yet; onboard with `/carpedata onboard <source>`)
| Source | Why | Notes |
|---|---|---|
| nflverse `ff_opportunity` | Expected yards and TDs from usage (opportunity models) | A strong usage prior; keyless |
| nflverse `nextgen_stats` | Separation, air yards, rush yards over expected | Keyless; weekly |
| nflverse play-by-play | EPA team ratings (`elite.py` already uses it) | Keyless; large |
| Open-Meteo | Wind and precipitation at outdoor stadiums (passing props) | Keyless and free; cite it |

## Owner decisions (not free, or key-gated)
| Source | Why | Rule |
|---|---|---|
| The Odds API (free tier, key) | Real player-prop lines and prices, which replace illustrative lines and enable edge and CLV | The key stays server-side; budget every call; the owner approves |
| Any paid feed | — | The owner decides; never added by an agent |

## Not allowed
Scraping sportsbooks or sites whose terms forbid it; routing around a 403 or 429 (no
browser spoofing); and presenting a social post or an unofficial report as data.
