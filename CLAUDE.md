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
| Fetch data (keyless, CC-BY-4.0) | `./.venv/bin/python -c "import nflprops,pathlib; nflprops.ensure_cache(pathlib.Path('cache'))"` |
| **Calibration audit** (the statistical gate) | `./.venv/bin/python scripts/calibration_audit.py cache/player_stats.csv` |
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
5. **Data:** nflverse is CC-BY-4.0, and the app shows its attribution. No NFL or team logos or
   marks (ADR-0007). An odds provider or other paid source is the owner's decision; its keys
   stay server-side.
6. **Small, reviewable changes:** one backlog item per branch (`<lane>/<item-id>-<slug>`) with
   a PR to `main`. Never push to `main`, never force-push, and never merge without the owner's yes.

## Workflow playbook: use these automatically, in these combinations
| Situation | Combination |
|---|---|
| Pick up the next MVP item | `/mvp-loop` (one item per iteration: kickoff, build, gates, review, PR) |
| New feature or multi-file change | `/kickoff` → `/build` → the gates → `/review` |
| **Any change to a probability, model, fit, simulation or calibration** | `/kickoff` → `/build` → **`/stat-rigor review`** (blocking, independent) → `/review` |
| A number goes into README, docs or app copy | `/stat-rigor claim` |
| Snapshot schema, signing, or the Python↔Swift boundary | `/snapshot-contract` → `/review` |
| iOS UI or project change | `/build` (XCTest) → `/ios-testflight check` → `/review` |
| Data source or odds-provider work | `/harden-datalink <source>` → `/datalink-audit`; the owner approves keys |
| Release candidate for TestFlight | `/ios-testflight release` → `/ship` (the owner archives and uploads) |
| Before any push or PR | `/review` |

## Loops
- **Driver:** `/loop /mvp-loop`. Self-paced; one backlog item per iteration; stops when
  `mvp_gate.py` exits 0 or every remaining item is blocked on the owner.
- **Gate watch:** `/loop 2h /mvp-loop status`. Read-only; reports the gate table and blocked items.
- **In season:** rebuild the snapshot weekly after nflverse updates (Tuesday), and re-run the
  calibration audit monthly. A stat that fails the gate is demoted in the next snapshot.

## Agent lanes (one lane per session; lanes do not trespass)
Architect (ADRs, contracts) · Statistician (`/stat-rigor`; reviews, never self-approves) ·
Model engineer (`src/nflprops`) · Backend (`ios/backend`, snapshot, signing) ·
iOS engineer (`ios/PropDesk`) · Release (`/ios-testflight`, version bumps, notes).
