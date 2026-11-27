# CLAUDE.md — nflprops / Prop Desk

Claude Code loads this file in every session in this repo. Keep it short and true.
Architecture and method decisions live in `docs/adr/`; they outrank this file's
summaries, and an agent never contradicts an Accepted ADR without a superseding one.

## Project
An honest NFL player-prop **decision-support** engine (Python, `src/nflprops/`) and its
iPhone app **Prop Desk** (SwiftUI, `ios/PropDesk/`). It reads a server-precomputed, signed
snapshot (`ios/backend/`). **Public repo:** everything committed is published.
- **Goal now:** an MVP on TestFlight. Plan and backlog: `docs/MVP_PLAN.md`.
  Readiness is measured, not asserted: `python scripts/mvp_gate.py`.
- **Not a sportsbook.** No wagering, no deposits, no bet placement, no sportsbook deep links,
  and no "lock", "guaranteed" or "can't lose" copy (ADR-0007).

## Commands
| Purpose | Command |
|---|---|
| Setup | `python3 -m venv .venv && ./.venv/bin/pip install -e '.[dev]'` |
| Lint | `./.venv/bin/ruff check src tests scripts` |
| Tests (hermetic, no network) | `./.venv/bin/python -m pytest tests/ -q` |
| Fetch data (keyless, CC-BY-4.0) | `./.venv/bin/python -c "import nflprops,pathlib; nflprops.ensure_cache(pathlib.Path('cache'))"`, then `scripts/check_sources.py` (current season and closing lines) |
| **Model v2 gate** (tune 2019–21, test 2022–23 and 2024–26) | `./.venv/bin/python scripts/model_v2_eval.py --legacy cache/player_stats.csv --current cache/stats_player_week_2025.csv cache/stats_player_week_2026.csv --games cache/games.csv` |
| v1 engine calibration audit | `./.venv/bin/python scripts/calibration_audit.py cache/player_stats.csv` |
| **Data-source health** (CarpeDATA) | `./.venv/bin/python scripts/check_sources.py --season 2026` |
| **MVP readiness gate** | `./.venv/bin/python scripts/mvp_gate.py` (exit 0 = TestFlight-ready) |
| Build snapshot | `./.venv/bin/python ios/backend/snapshot_server.py --stats cache/player_stats.csv --out <path>` |
| iOS project | `cd ios/PropDesk && xcodegen generate` (macOS only; CI runs it, ADR-0006) |

A change is done only when the gates relevant to it pass, and their output is pasted in the PR.

## Non-negotiables
1. **No fabricated numbers.** Every figure shown in the app or docs is reproducible by a
   command, or is labelled as illustrative. A prop line without a real, timestamped market
   source is labelled "illustrative line" (ADR-0004).
2. **Statistical validity standard (ADR-0003).** Strictly temporal splits; randomized PIT for
   discrete and zero-inflated stats; proper scoring rules (Brier, log loss) against a naive
   baseline; player-clustered bootstrap CIs. A probability is shown as decision-grade only for
   a stat that passes the calibration gate; otherwise it is hidden or labelled experimental.
3. **Independent review of model changes.** The agent that changes a probability model does
   not approve it. `/stat-rigor review` runs in a separate session (or by the owner).
4. **Secrets:** never read `.env*`; never print, log or commit keys, signing keys, `.p8` or
   `.p12` files, or provisioning profiles. The app holds **no secret**: the snapshot is
   verified with a **public** key (ADR-0002).
5. **Data (CarpeDATA, `docs/DATA_SOURCES.md`):** free keyless sources first; 403 and 429 stop
   and are reported; stale data is labelled. nflverse is CC-BY-4.0, and the app shows its attribution. No NFL or team logos or
   marks (ADR-0007). An odds provider or other paid source is the owner's decision; its keys
   stay server-side.
6. **Small, reviewable changes:** one backlog item per branch (`<lane>/<item-id>-<slug>`) with
   a PR to `main`. Never push to `main`, never force-push, and never merge without the owner's yes.

## Workflow playbook: use these automatically, in these combinations
| Situation | Combination |
|---|---|
| Pick up the next MVP item | `/mvp-loop` (one item per iteration: kickoff, build, gates, review, PR) |
| **Anything touching a data source, the cache, freshness or a key** | **`/carpedata` first** (`check` / `onboard` / `incident` / `gaps`) |
| New feature or multi-file change | `/kickoff` → `/build` → the gates → `/review` |
| **Any change to a probability, model, fit, simulation or calibration** | `/kickoff` → `/build` → **`/stat-rigor review`** (blocking, independent) → `/review` |
| A number goes into README, docs or app copy | `/stat-rigor claim` |
| Snapshot schema, signing, or the Python↔Swift boundary | `/snapshot-contract` → `/review` |
| **Any screen, flow, chart or copy in the app** | **`/ios-ux design <screen>`** → `/build` (XCTest + previews) → **`/ios-ux review`** → `/ios-testflight check` → `/review` |
| iOS project or build change | `/build` (XCTest) → `/ios-testflight check` → `/review` |
| Before each TestFlight build, or after testers report | `/ios-ux test` (5-tester round, SUS ≥ 75) |
| Data source or odds-provider work | `/carpedata onboard <source>` → `/review`; the owner approves keys |
| Release candidate for TestFlight | `/ios-testflight release` → `/ship` (the owner archives and uploads) |
| Before any push or PR | `/review` |

## Loops (ready-to-paste prompts for everything: `docs/PROMPTS.md`)
- **Driver:** `/loop /mvp-loop`. Self-paced; one backlog item per iteration; stops when
  `mvp_gate.py` exits 0 or every remaining item is blocked on the owner.
- **Gate watch:** `/loop 2h /mvp-loop status`. Read-only; reports the gate table and blocked items.
- **Data watch:** `/loop 6h /carpedata check` in season (one request per source).
- **In season:** rebuild the snapshot weekly after nflverse updates (Tuesday), and re-run the
  calibration audit monthly. A stat that fails the gate is demoted in the next snapshot.

## Agent lanes (one lane per session; lanes do not trespass)
Architect (ADRs, contracts) · Statistician (`/stat-rigor`; reviews, never self-approves) ·
Model engineer (`src/nflprops`) · Backend (`ios/backend`, snapshot, signing) ·
iOS engineer (`ios/PropDesk`) · Release (`/ios-testflight`, version bumps, notes).
