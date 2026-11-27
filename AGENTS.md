# Controlled agent development policy

This repository uses AI agents as drafting and analysis tools. Agents are not
release authorities.

## Mission boundary

Improve the NFL player-prop decision engine incrementally while preserving its
honesty constraints: no guaranteed-win claims, no invented market data, no
silent calibration claims, and no client-side provider secrets.

## Required change sequence

1. State the requirement ID and risk ID affected by the change.
2. Inspect the relevant implementation and existing tests before editing.
3. Make the smallest coherent change. Do not mix refactors and behavior changes.
4. Add or update tests that demonstrate the acceptance criteria and failure mode.
5. Run the required checks in `docs/SOFTWARE_LIFECYCLE_PLAN.md`.
6. Update `docs/TRACEABILITY.md` when behavior, risk controls, or verification changes.
7. Use a branch and pull request. Never push directly to `main`.

## Prohibited autonomous actions

Agents must not:

- merge or enable auto-merge;
- weaken, skip, or delete a test or CI gate merely to make a check pass;
- change odds, staking, calibration, or risk thresholds without an approved requirement;
- introduce a dependency, external data source, credential, or telemetry sink without human approval;
- expose secrets in source, logs, fixtures, screenshots, or generated artifacts;
- claim IEC 62304 certification or medical-device status;
- modify more than the stated change scope without stopping and reporting the need;
- treat synthetic fixtures as real-world validation evidence.

## Stop conditions

Stop and request human direction when requirements conflict, real-data evidence
is unavailable, a safety or financial-risk control would be reduced, a secret
or paid service is required, or the proposed change cannot be independently
verified. Report failed checks and known debt; do not hide them.
