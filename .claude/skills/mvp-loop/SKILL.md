---
name: mvp-loop
description: The orchestration loop that moves Prop Desk to a TestFlight MVP one backlog item per iteration. Use as `/loop /mvp-loop` (self-paced) or `/mvp-loop status`. It picks the next unblocked item from docs/MVP_PLAN.md, runs the right skill combination for that item's lane, gates it, and opens a PR. It never merges and never works on an owner-blocked item.
---

# mvp-loop: one item, fully gated, per iteration

## Each iteration
1. **Sync.** Fetch `main`; skip any item that already has an open PR or branch.
2. **Measure.** Run `python scripts/mvp_gate.py` and keep the table. It is the scoreboard.
3. **Pick.** Take the first item in `docs/MVP_PLAN.md` whose status is `todo`, whose
   dependencies are `done`, and that is not `owner`-blocked. **One item only.**
4. **Run its lane's combination** (CLAUDE.md playbook):
   - model, stats or calibration: `/kickoff` → `/build` → audit before and after →
     **stop and request `/stat-rigor review` from a separate session**. Never self-approve.
   - backend or snapshot: `/kickoff` → `/build` → `/snapshot-contract`.
   - iOS: `/kickoff` → `/build` → `/ios-testflight check` (macOS CI must be green).
   - docs or copy with numbers: `/stat-rigor claim`.
5. **Gate.** Run lint, pytest, the relevant audit, and `mvp_gate.py` again. The item is done
   only if its acceptance criteria in `MVP_PLAN.md` are met by command output.
6. **Ship the slice.** Run `/review`, then open a PR with the gate output pasted in. Set the
   item to `review` in `MVP_PLAN.md` within the same PR.
7. **Report** one line: the item, the PR, the gate delta, and the next item.

## `status` (read-only)
Report the gate table, items by status, owner-blocked items with the exact decision needed,
and open PRs awaiting review.

## Stop conditions (end the loop and report)
- `mvp_gate.py` exits 0: hand off to `/ios-testflight release`.
- Every remaining item is `owner`-blocked or in `review`.
- A gate got worse and the cause is unknown: stop, do not push, and report.
- Two consecutive iterations without a merged-ready PR.

## Never
Work on two items at once, weaken a gate or threshold to go green, merge, push to `main`,
or touch signing, credentials or provider keys.
