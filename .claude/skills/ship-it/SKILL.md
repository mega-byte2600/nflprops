---
name: ship-it
description: Standing owner instruction for nflprops. When the owner says "ship it", "push it", "do it", "send it" or "merge it" (typed or by voice), merge every routine open PR that is green, in stack order, without asking again; stop only for changes on the needs-owner list. Use whenever one of those phrases arrives about this repo.
---

# ship-it: one phrase, routine work merges itself

The owner's standing instruction (2026-11-27): when they say **ship it / push it / do it /
send it / merge it**, Claude merges routine work without asking each time. Only something
very different, new or unusual comes back to them. This skill applies that rule the same way
every time.

## Routine: merge without asking
A PR merges when **all** of these hold:
1. CI is green on its head commit (every check `success`).
2. Its gates pass, with their output in the PR (lint, pytest, plus `mvp_gate.py`, the audit
   or `check_sources.py` where the change touches them). No gate or threshold was weakened.
3. It stays inside Accepted ADRs and the current `docs/MVP_PLAN.md` items.
4. If it changes a probability or model, an independent `/stat-rigor review` posted
   **APPROVE** on the PR.
5. Its base PR, if it is stacked, has merged first. Merge in stack order and retarget each
   next PR to `main`.

Typical routine work: backlog items, bug fixes, tests, docs, UI built to ADR-0008, a weekly
snapshot or data refresh, and dependency patch bumps.

## Needs the owner: stop and ask in one line, then carry on with the rest
- a new ADR, or a change to an Accepted ADR's decision;
- a model change without an independent APPROVE, or one whose audit got worse;
- a snapshot schema MAJOR bump, or any change to signing, keys, secrets or `.github/workflows`
  permissions;
- a new data source that needs a key, costs money, or changes an established source's
  contract;
- deleting data, history or branches; force-pushes;
- a TestFlight or App Store release, its review notes, age rating or privacy answers;
- red CI, or a PR with a failing or skipped gate;
- anything outside the MVP plan, or a PR over about 500 changed lines of hand-written code.

## Steps
1. List the open PRs: `gh api "repos/mega-byte2600/nflprops/pulls?state=open"`.
2. Classify each one as routine or needs-owner, giving the rule it falls under.
3. Merge the routine ones in stack order:
   `gh api -X PUT repos/mega-byte2600/nflprops/pulls/<n>/merge -f merge_method=merge`.
   Retarget the next one in the stack (`PATCH .../pulls/<n> -f base=main`), then wait for its
   CI.
4. Check that `main` CI is green after each merge. If it goes red, stop merging and report.
5. Reply with one table (PR | action | reason) and one line per needs-owner item saying exactly
   what to decide.

## Permission
Merging needs the owner's allow rule in `.claude/settings.json` (see `docs/PROMPTS.md`, "Ship
it"). Without it, Claude prepares everything and gives the owner the one-tap merge links
instead of retrying or working around the block.
