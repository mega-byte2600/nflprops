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
