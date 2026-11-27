# Prompts: copy, paste, run

Each prompt is self-contained. Paste it into a Claude Code session opened on this repo.
Skills: `/mvp-loop`, `/stat-rigor`, `/carpedata`, `/snapshot-contract`, `/ios-testflight`, plus
the global `/kickoff`, `/build`, `/review` and `/ship`. Rules: `CLAUDE.md`. Decisions: `docs/adr/`.

## 0. Ship it (voice-friendly)
Say or type any of these: **"ship it"**, **"push it"**, **"do it"**, **"send it"**, **"merge it"**.
That runs `/ship-it`: every routine green PR merges in stack order, and only the needs-owner
list comes back to you. To run it as a loop:
```
/loop 30m /ship-it
```
**One-time setup (you add this yourself; Claude may not grant itself permissions).** Create
`.claude/settings.json` in this repo (on GitHub: Add file, then Create new file), or add these
lines to your own `~/.claude/settings.json`:
```json
{
  "permissions": {
    "allow": [
      "Bash(gh api -X PUT repos/mega-byte2600/nflprops/pulls/*/merge*)",
      "Bash(gh api -X PATCH repos/mega-byte2600/nflprops/pulls/*)"
    ]
  }
}
```
It allows merging and retargeting PRs in this repo only. Nothing else changes.

## 1. Drive the MVP (the main loop)
```
/loop /mvp-loop
```
Self-paced. One backlog item per iteration: pick, kickoff, build, gates, review, PR. It stops
when `scripts/mvp_gate.py` exits 0 or everything left needs me. Model changes pause for an
independent `/stat-rigor review`.

## 2. Status, any time (read-only)
```
/mvp-loop status
```

## 3. Independent statistical review (run in a NEW session, never the author's)
```
/stat-rigor review <PR number or branch>. You did not write this change. Run the
calibration audit on main and on the branch, paste the before/after table per stat (gap
with CI, Brier skill with CI, gate), check every ADR-0003 rule, and post APPROVE, CHANGES
or REJECT on the PR.
```

## 4. Data health (CarpeDATA)
```
/carpedata check
```
In season, as a loop (one request per source, so this is safe):
```
/loop 6h /carpedata check
```

## 5. Find and use more free data
```
/carpedata gaps. Then onboard the top free source with /carpedata onboard <source>, open
it as a PR, and add a backlog item for the model to consume it. The item must show skill
gained in the audit before it is used.
```

## 6. iOS readiness and release
```
/ios-testflight check
```
```
/ios-testflight release, then /ship. Give me the exact upload steps for my Mac.
```

## 6b. UI/UX (evidence-based iPhone design)
Design a screen before building it:
```
/ios-ux design <This Week | Prop detail | Search | Method>. Follow ADR-0008: the answer first
as a natural frequency, a 20-dot quantile dotplot, freshness always visible, every state
designed, Dynamic Type at AX5, VoiceOver sentences. Then /build it with SwiftUI previews for
default, AX5 and dark, and open a PR with screenshots.
```
Review the UI before every TestFlight build:
```
/ios-ux review <PR>. Score every screen on Nielsen's 10 heuristics and the ADR-0008
non-negotiables from the CI screenshots (default and AX5, light and dark); run the
accessibility audit; severity 3-4 blocks. Post the table on the PR.
```
Plan a tester round:
```
/ios-ux test. Write the 5-tester round plan (3 tasks, success criteria, SUS), and after the
round turn the top 3 findings into backlog items with evidence.
```
Loop the UI to done:
```
/loop /mvp-loop, prioritising I-items, and run /ios-ux design before and /ios-ux review after
each one.
```

## 7. Parallel lanes (one session each; they never edit the same files)
Model engineer:
```
You are the Model engineer for nflprops. Take the next todo S-item in docs/MVP_PLAN.md.
Follow ADR-0003. /kickoff, then /build; run scripts/model_v2_eval.py before and after; open a
PR with both tables; request /stat-rigor review. Touch only src/nflprops, tests and
scripts. Never self-approve.
```
Backend and contract:
```
You are the Backend engineer. Take the next todo B-item in docs/MVP_PLAN.md. Use
/snapshot-contract for every boundary change (golden fixture, Ed25519, schema version).
Touch only ios/backend, tests and the fixtures. PR plus /review.
```
iOS engineer:
```
You are the iOS engineer. Take the next todo I-item in docs/MVP_PLAN.md. Follow ADR-0005,
0006, 0007 and 0008; /ios-ux design first and /ios-ux review last. Builds are verified only by the macOS CI job. Touch only ios/PropDesk and
.github/workflows. /ios-testflight check, then a PR with screenshots.
```

## 8. Scheduled tasks (in season)
Weekly snapshot, Tuesday after nflverse updates:
```
Run /carpedata check. If stats_player_week and schedules are FRESH, rebuild the snapshot
with the v2 model and the latest audit gates, run the tests and the snapshot contract tests,
and open a PR titled "Weekly snapshot <date>". If any source is STALE or UNAVAILABLE, do not
rebuild; report it.
```
Monthly re-audit:
```
/stat-rigor audit. Re-run scripts/model_v2_eval.py and scripts/calibration_audit.py on the
latest data. Update docs/audit/latest.json. If any stat's gate flips to FAIL, open a PR that
marks it experimental in the snapshot and tell me.
```

## 9. Any new feature (the generic combination)
```
/kickoff <feature>. Then /build. If it changes a probability, also /stat-rigor review in a
new session. If it crosses Python and Swift, /snapshot-contract. Then /review and a PR.
Paste the gate outputs in the PR.
```

## Efficiency rules that make these loops fast
- One item per iteration, the smallest vertical slice, and gate output in every PR.
- Run lanes in parallel only on disjoint files (see section 7).
- Data checks cost one request per source; never poll a key-gated API to check its health.
- A failing gate stops the loop. Never weaken a threshold to go green.
