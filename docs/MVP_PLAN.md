# MVP plan: Prop Desk to TestFlight

Driver: `/loop /mvp-loop`. Scoreboard: `python scripts/mvp_gate.py`. Decisions: `docs/adr/`.

Status values: `todo`, `review` (PR open), `done` (merged), `owner` (needs the owner).
An item is done only when its acceptance criteria are shown by command output in its PR.

## Owner decisions (block the items that depend on them)
| ID | Decision | Unblocks | Status |
|---|---|---|---|
| O1 | Accept ADR-0001 to 0007 (or amend them) | everything | owner |
| O2 | Apple Developer Program membership, team, and bundle ID (`com.emporion.propdesk`?) | R2 | owner |
| O3 | Create the Ed25519 production signing key and store it as a GitHub Actions secret | B4 | owner |
| O4 | Odds provider and key, for real lines (post-MVP; the MVP uses illustrative lines) | post-MVP | owner |

## M1: statistical correctness (Statistician + Model engineer)
| ID | Item | Depends | Acceptance (measured) | Status |
|---|---|---|---|---|
| S1 | Correct PIT in `calibration.py`: score against the sampled mixture, randomized at atoms; strictly temporal split in `cli calibration` | O1 | A synthetic perfectly specified Poisson, NB and zero-inflated gamma each score mean-u in [0.49, 0.51] (pytest); the CLI trains on seasons < min(test) | done |
| S2 | TD: apply the Poisson once (or a hurdle model) in `marginals` | S1 | Audit: TD Brier below as-shipped (0.215 and 0.187) and skill > 0; `/stat-rigor review` APPROVE | done |
| S3 | Recency weighting plus empirical-Bayes shrinkage toward a position/role prior, tuned on 2021 only | S2 | Audit on 2022–23: skill > 0 with the bootstrap CI excluding 0 for at least 2 yardage stats; `/stat-rigor review` APPROVE | done |
| S4 | Held-out calibration map (isotonic, or beta for small samples), fit on season t−1 and tested on t | S3 | Rolling-origin audit (test 2023, then 2024): at least 2 stats gate PASS; `docs/audit/latest.json` committed | done |
| S6 | Usage prior from free `snap_counts` and `ff_opportunity` (CarpeDATA onboard first) | S4 | `model_v2_eval.py`: Brier skill improves beyond the 2024–26 CI of v2 for at least 2 stats; `/stat-rigor review` APPROVE | todo |
| S7 | Availability from free `injuries` (Out/Doubtful players excluded; Questionable adjusts) | S4 | Audit shows no worse calibration; fewer predictions for players who did not play | todo |
| S5 | The snapshot uses projection v2 and carries per-stat gate results; `p_over` is null for failing stats, which are marked `experimental` | S4, B2 | pytest: a failing stat has a null `p_over` in the snapshot | todo |

## M1b: data (CarpeDATA)
| ID | Item | Depends | Acceptance | Status |
|---|---|---|---|---|
| D1 | Free source layer (`sources.py`): current-season stats, closing lines, snaps, injuries, depth charts; resilient fetching; health check | — | `check_sources.py`: all FRESH; hermetic tests for 403/429/5xx/schema/stale | done |
| D2 | `ensure_cache` and the snapshot builder read the combined 1999–present table via `sources.player_weeks` | D1 | The snapshot `data_as_of` is the latest nflverse week | todo |

## M2: contract and integrity (Backend)
| ID | Item | Depends | Acceptance | Status |
|---|---|---|---|---|
| B1 | Ed25519 envelope over exact bytes (`cryptography`); remove HMAC | O1 | pytest: sign/verify passes; a one-byte tamper fails; an unknown `key_id` fails | todo |
| B2 | Schema 2.0: `line_source`, `line_as_of`, `q10`/`q90`, `data_as_of`, `audit_as_of`, per-stat gates; golden fixture | B1 | pytest golden test; the schema doc is in `/snapshot-contract` | todo |
| B3 | Replace the hard-coded lines with illustrative lines (historical median + 0.5), labelled | B2 | pytest: no prop has a non-null `edge` with an illustrative `line_source` | todo |
| B4 | Workflow that builds and signs the snapshot and publishes it to GitHub Pages | B3, O3 | The workflow run is green; the published file verifies with the public key | owner |

## M3: iOS app (iOS engineer)
| ID | Item | Depends | Acceptance | Status |
|---|---|---|---|---|
| I1 | `project.yml`: resources (`Assets.xcassets` + 1024 `AppIcon`, bundled snapshot, `PrivacyInfo.xcprivacy`) and a `PropDeskTests` target | O1 | `mvp_gate.py` iOS rows pass | done |
| I2 | macOS CI job: `xcodegen` + `xcodebuild build test` on a simulator, unsigned | I1 | The job is green on the PR | done |
| I3 | Swift Ed25519 verification (CryptoKit) with the public key only; reject unknown MAJOR; fetch a newer snapshot and cache the last verified one | B2, I2 | XCTest: the golden file verifies; tampered, unknown `key_id` and unknown MAJOR fail | todo |
| I4 | UI per ADR-0005 and ADR-0008: three tabs (This Week by game, Search, Method), natural-frequency answer, 20-dot quantile dotplot, line-source label, experimental label, Method screen (calibration table, nflverse CC-BY-4.0 attribution, 1-800-GAMBLER) | I3, S5 | XCTest/UI test; `mvp_gate.py` copy rows pass; screenshots in the PR | todo |
| I6 | XCUITest screenshots (default and AX5, light and dark) as CI artifacts, plus the accessibility audit test | I2 | Artifacts on the PR; the audit test passes | review |
| U1 | `/ios-ux review` of all four screens; no severity 3–4 issues | I4, I6 | The review table is posted on the PR | todo |
| U2 | First 5-tester TestFlight round (`/ios-ux test`): SUS ≥ 75, task success ≥ 90%, comprehension ≥ 80% | R2 | The findings doc is in `docs/ux/` | owner |
| I5 | Accessibility and quality: Dynamic Type at the largest size, VoiceOver labels, dark mode, no crash on an empty or stale snapshot | I4 | XCTest plus screenshots at the accessibility size | todo |

## M4: release (Release)
| ID | Item | Depends | Acceptance | Status |
|---|---|---|---|---|
| R1 | README and docs: replace the "honest negative" table with the audited numbers (`/stat-rigor claim`) | S4 | Every number in the README reproduces from a command | todo |
| R2 | Release candidate: build number bump, `ios/RELEASE_NOTES.md`, App Review notes; the owner archives and uploads to internal TestFlight | all, O2 | `mvp_gate.py` exits 0; the owner confirms build 1 is in TestFlight | todo |
