---
name: stat-rigor
description: The Chief Applied Statistician's gate for nflprops. Use whenever a change touches a probability, fit, simulation, copula, calibration, ranking, staking or any number shown to users, and before a number goes into the README, docs or app copy. Modes: review (blocking review of a diff), audit (run the calibration gate on real data), claim (verify one stated number). Never self-approve a model change.
---

# stat-rigor: textbook rigor, measured, never asserted

Governing decision: `docs/adr/ADR-0003-statistical-validity-standard.md`. Baseline evidence:
`docs/STAT_AUDIT_2026-11-27.md`. The standard is graduate-level applied statistics:
Gneiting & Raftery (2007) on proper scoring; Czado, Gneiting & Held (2009) on randomized PIT;
Gelman et al., *BDA3*, ch. 5 on partial pooling; Hyndman & Athanasopoulos, *FPP3*, §5.10 on
rolling-origin evaluation; Efron & Tibshirani (1993) on the bootstrap; Kelly (1956) and Thorp
(2006) on staking.

## Rules (a violation is a blocker)
1. **Temporal integrity.** Train only on seasons strictly before the test season. Grep the diff
   for `~df.season.isin(` and any random split of player-games; both are leakage.
2. **Correct PIT.** Score against the CDF of exactly what the simulator samples, including the
   zero-inflation mixture, randomized at every atom. A pooled KS p-value over dependent
   player-games is descriptive only.
3. **Proper scoring against a baseline.** Report Brier and log loss at P(over line), plus the
   Brier skill score against the player's historical hit rate. "Better" means a higher skill
   score whose player-clustered bootstrap CI excludes 0, not a lower raw loss on one run.
4. **Self-validating scorers.** Any new scorer or metric ships with a synthetic test in which
   a perfectly specified model scores as calibrated (mean-u ≈ 0.5 ± 0.01, Brier at its
   theoretical value).
5. **Uncertainty is shown.** Every reported effect has a CI. CIs on player-game data are
   player-clustered.
6. **Winner's curse.** Ranked lists use shrunken edges; an edge is shown only when its CI
   lower bound is above 0.
7. **Staking stays off** until a stat passes the gate **and** a real de-vigged market price
   exists (ADR-0004). Then fractional Kelly only.
8. **No fabricated or unanchored numbers.** Every number has a command that reproduces it,
   or is labelled illustrative.

## Modes

### `review <branch|PR>`: blocking, independent
Run this in a session that did not write the change.
1. List changed files under `src/nflprops/` and `ios/backend/`, and any docs that contain
   numbers.
2. Check rules 1–8 line by line.
3. Run `python scripts/calibration_audit.py cache/player_stats.csv --json after.json` on the
   branch and on `main` (`before.json`). Paste a before/after table per stat: gap, gap CI,
   Brier, skill score and gate.
4. Verdict: `APPROVE` (no stat got worse beyond its CI and the claims match the table),
   `CHANGES` (with an exact list), or `REJECT`. Post it on the PR.

### `audit`
Run the audit (as shipped, plus any flags for the proposed fixes). Update the per-stat gate
status that the snapshot uses, and record the table in `docs/` with its date and command.

### `claim "<text>"`
Find the number's source command and re-run it. If the number doesn't reproduce exactly
(allowing for a printed rounding), the claim is corrected or removed. Never round up a result.

## Output
A short table (stat | before | after | CI | gate) plus a verdict. VERIFIED means a command
measured it; VALIDATED means it meets the owner's expectation. Label which.
