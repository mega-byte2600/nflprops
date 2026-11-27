# Statistical audit, 2026-11-27 (Chief Applied Statistician)

Independent audit of the calibration claims in the README and `docs/BML_LOOP.md`. Real nflverse
`player_stats` data (CC-BY-4.0), seasons 2003–2024. Reproduce with:

```
python scripts/calibration_audit.py cache/player_stats.csv                        # as shipped
python scripts/calibration_audit.py cache/player_stats.csv --td-single-inflation  # proposed TD fix
```

Test seasons 2022–23; training uses seasons before 2022 only. Lines are book-style: 0.5 for TDs,
and the player's historical median + 0.5 for yards. CIs are a player-clustered bootstrap
(300 resamples, seed 2026).

## 1. The published result is mostly a measurement artifact
| stat | published mean-u (repo method) | randomized mean-u against the sampled mixture |
|---|---|---|
| passing_yards | 0.458 | 0.475 |
| rushing_yards | 0.341 | 0.444 |
| receiving_yards | 0.401 | 0.468 |
| rushing_tds | 0.762 | 0.574 → **0.474** with the TD fix |
| receiving_tds | 0.780 | 0.574 → **0.473** with the TD fix |

The causes, each verified:
- **The PIT on discrete counts is not randomized.** A perfectly specified Poisson model scores
  mean-u 0.78 (λ = 0.35), 0.73 (0.5) and 0.68 (0.8) on simulated data under the repo's method.
- **The PIT ignores zero-inflation.** A perfectly specified zero-inflated gamma scores 0.30,
  0.37 and 0.45 at P(active) = 0.60, 0.75 and 0.90. This matches the rushing-yards "0.341".
- **Look-ahead leakage.** "Train < 2022" in fact trained on every season except 2022–23,
  including 2024.

## 2. A real model bug: double zero-inflation on TDs
`fit_player` fits λ on all games, zeros included; `rvs` and `over_prob` then multiply by
`p_active` a second time.

| | rushing_tds | receiving_tds |
|---|---|---|
| actual anytime-TD rate | 0.274 | 0.228 |
| model as shipped | 0.116 | 0.095 |
| Poisson applied once | 0.313 | 0.290 |
| Brier (shipped → fixed) | 0.215 → 0.192 | 0.187 → 0.172 |

## 3. The decision quantity against a naive baseline
The baseline is the player's own historical hit rate at the same line (Laplace-smoothed).

| stat | predicted P(over) | actual | gap (95% CI) | Brier skill vs baseline | gate |
|---|---|---|---|---|---|
| passing_yards | 0.486 | 0.463 | −0.023 [−0.084, +0.038] | −0.004 | FAIL (no skill) |
| rushing_yards | 0.441 | 0.373 | −0.067 [−0.098, −0.036] | +0.015 | FAIL (biased) |
| receiving_yards | 0.488 | 0.454 | −0.034 [−0.058, −0.007] | −0.005 | FAIL |
| rushing_tds (fixed) | 0.313 | 0.274 | −0.040 [−0.084, −0.000] | +0.003 | FAIL (biased) |
| receiving_tds (fixed) | 0.290 | 0.228 | −0.062 [−0.080, −0.043] | +0.015 | FAIL (biased) |

**Verdict.** Once correctly measured, the engine is roughly as good as a player's own historical
hit rate, and no better. That is not a failure of honesty; it is the baseline the model must
beat. The remaining bias is systematically **optimistic** (it predicts overs too often),
which is the classic signature of regression to the mean: players are fit on their own history
with no shrinkage and no recency weighting.

## 4. Prescribed fixes, in order (each measured by the audit before and after)
1. TD: apply the Poisson once (or a proper hurdle model). Then fix the PIT and the leakage in
   `calibration.py`, with synthetic self-tests.
2. Recency weighting (exponentially weighted history) plus empirical-Bayes shrinkage toward a
   position/role prior. Tune the shrinkage on 2021, test on 2022–23 (rolling origin).
3. Usage covariates (snap share, targets, carries) and team context (the `elite.py` EPA prior)
   as location shifts, again measured.
4. A post-hoc calibration map (isotonic, or beta for small samples) fit on a held-out season.
5. Only then: display as decision-grade the stats that pass the ADR-0003 gate.

## 5. Fixes implemented and measured (same day)
- **v1 engine:** randomized PIT against the sampled mixture (`calibration.randomized_pit`),
  strictly temporal training in `nflprops calibration`, and count families no longer
  double-inflated (`p_active = 1.0`). `nflprops calibration` now reports TD mean-u 0.476 and
  0.473, down from 0.762 and 0.780.
- **Projection v2** (`src/nflprops/projection.py`): one-step-ahead, recency-weighted (EW
  half-life), empirical-Bayes shrinkage to the previous season's position mean, anchored to
  the **free closing-line implied team total**, an out-of-sample predictive dispersion, and
  Platt recalibration. Everything is tuned and recalibrated on 2019–21 only.

`python scripts/model_v2_eval.py ...` (`docs/audit/latest.json`); player-clustered bootstrap:

| stat | test 2022–23: gap [95% CI] / skill [95% CI] | test 2024–26: gap [95% CI] / skill [95% CI] | gate |
|---|---|---|---|
| passing_yards | +0.004 [−0.032, +0.037] / +0.046 [+0.025, +0.066] | −0.012 [−0.037, +0.013] / +0.024 [+0.001, +0.042] | PASS |
| rushing_yards | −0.011 [−0.038, +0.018] / +0.044 [+0.017, +0.071] | +0.000 [−0.021, +0.019] / +0.041 [+0.020, +0.062] | PASS |
| receiving_yards | −0.015 [−0.032, +0.000] / +0.025 [+0.012, +0.039] | −0.013 [−0.028, +0.000] / +0.027 [+0.018, +0.038] | PASS |
| rushing_tds | −0.010 [−0.025, +0.003] / +0.047 [+0.032, +0.063] | −0.002 [−0.014, +0.012] / +0.033 [+0.021, +0.044] | PASS |
| receiving_tds | −0.009 [−0.017, −0.001] / +0.048 [+0.038, +0.059] | −0.007 [−0.013, −0.001] / +0.047 [+0.039, +0.055] | PASS (\|gap\| ≤ 0.02) |

Tuned market elasticity: beta = 1.0 for TDs, 0.5 for yards. Platt changes the skill by at
most 0.003, so the model is calibrated before recalibration.

**What this does and does not show.** v2 beats a strong naive baseline (the player's
last-16 hit rate at a book-style line) and is calibrated out of sample, including the
current season. It does **not** show an edge over sportsbook prices: those lines embed far
more information than a historical median. Edge claims need real prop prices (ADR-0004, O4).
The closing total is known at kickoff, so the anchor is valid for decisions made near
kickoff; earlier decisions should use the opening total (a known, small optimism).

## 6. Independent review (`/stat-rigor`, separate agent) and corrected results
**Verdict: CHANGES, no blocker.** The reviewer found no leakage (a perturbation test changed
nothing at or before the perturbed game), confirmed the math, and reproduced every number. It
raised five findings:
1. The baseline was not recalibrated like the model, which inflated skill by 27–63%.
   **Fixed:** the baseline now gets the same held-out Platt fit, and a stacked baseline is added.
2. The gate pooled 2024–26 while the ADR said "latest season". **Fixed:** ADR-0003 is amended
   (a pooled latest window of at least 1,000 games, with per-season results reported).
3. Negative rushing yards scored u = 0 in the randomized PIT. **Fixed:** they are clipped to
   the zero atom, as the simulator does, with a synthetic test.
4. The EW effective n overstated the Kish value. **Fixed:** the exact formula is used, with a test.
5. Bootstrap CIs hold the tuned parameters fixed. **Disclosed** above.

Corrected 2024–26 results (`docs/audit/latest.json`):

| stat | gap [95% CI] | skill vs recalibrated naive [95% CI] | skill vs stacked [95% CI] | gate |
|---|---|---|---|---|
| passing_yards | −0.012 [−0.037, +0.014] | +0.017 [−0.005, +0.033] | +0.015 [−0.003, +0.030] | **FAIL**: experimental |
| rushing_yards | +0.000 [−0.022, +0.019] | +0.027 [+0.011, +0.042] | +0.018 [+0.002, +0.031] | PASS |
| receiving_yards | −0.013 [−0.028, +0.000] | +0.019 [+0.012, +0.027] | +0.014 [+0.006, +0.021] | PASS |
| rushing_tds | −0.002 [−0.014, +0.012] | +0.019 [+0.009, +0.028] | +0.014 [+0.005, +0.023] | PASS |
| receiving_tds | −0.007 [−0.013, −0.001] | +0.017 [+0.012, +0.023] | +0.012 [+0.007, +0.017] | PASS |

The edge is real but modest: about a 2% Brier improvement on the strongest naive comparison.
Per season, receiving yards in 2025 was optimistic (gap −0.043), and passing yards in 2024 had
no skill. The headline claim in §5 is superseded by this table.
