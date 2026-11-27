# ADR-0003: Statistical validity standard and the calibration gate

Status: Proposed (2026-11-27). Owner: the Statistician lane (`/stat-rigor`).

## Context: the 2026-11-27 audit
The README's headline result says "raw per-player fits are not calibrated" (mean-u 0.34–0.78).
An independent audit on the same real nflverse data (2003–2024) found that result is largely an
**artifact of the measurement**, plus one model bug. See `docs/STAT_AUDIT_2026-11-27.md` and
reproduce with `scripts/calibration_audit.py`.

1. **Non-randomized PIT on discrete stats.** `u = F(y)` for a Poisson count is not Uniform(0,1)
   even when the model is exactly right: for λ = 0.35, E[u] = 0.78 (simulated). Randomized PIT
   (Czado, Gneiting & Held, 2009, *Biometrics* 65:1254) fixes this.
2. **The PIT ignores the zero-inflation mixture.** For a zero-inflated gamma or normal fit, the
   scorer used the active-only CDF, so every zero game scored u = 0. A perfectly calibrated
   model with P(active) = 0.75 scores mean-u = 0.37.
3. **Look-ahead leakage.** The "leakage-free" backtest trained on all non-test seasons,
   including 2024, which comes after the 2022–23 test period.
4. **Model bug: double zero-inflation on Poisson TDs.** λ is fit on all games (zeros included),
   and `rvs` and `over_prob` then multiply by `p_active` again. Anytime-TD probability is
   understated about 2.4× (predicted 0.116 vs actual 0.274, rushing TDs, 2022–23).
   Applying the Poisson once: predicted 0.313, and Brier improves from 0.215 to 0.192.

With these fixes, passing yards are calibrated at book-style lines: the gap between predicted
and realized is −2.3 points, with a 95% player-clustered CI of [−8.4, +3.8]. Rushing and
receiving yards are modestly over-optimistic (−6.7 and −3.4 points, both significant), which
is consistent with regression to the mean.

## Decision: the standard every model change must meet
1. **Strictly temporal evaluation.** Train on seasons before the test season. Use
   rolling-origin evaluation (Hyndman & Athanasopoulos, *FPP3*, §5.10). No future season in
   training, ever.
2. **Correct PIT.** Score against the CDF of exactly what the simulator samples (the
   mixture). Randomize at every atom: discrete counts and the zero mass.
3. **Proper scoring rules against a naive baseline.** Report Brier (Brier, 1950) and log loss at
   the decision quantity (P(over line)), and a Brier skill score against a baseline (the
   player's historical hit rate at that line). A model that cannot beat the baseline adds no
   value (Gneiting & Raftery, 2007, *JASA* 102:359).
4. **Dependence-aware uncertainty.** Player-games are not independent, so CIs use a player-
   clustered bootstrap (≥ 300 resamples). A pooled KS test over dependent observations is
   reported only as descriptive, never as a gate.
5. **Reliability, not just the mean.** Reliability diagrams with 10 quantile bins. A
   calibration correction (isotonic, or Platt/beta for small samples) is fit on one held-out
   season and evaluated on a later one, never on the same data.
6. **Winner's curse when ranking.** Ranking many props by estimated edge selects noise. Any
   ranked list shrinks edges (empirical-Bayes) and shows an edge only when the lower bound of
   its CI is above zero.

## Decision: the calibration gate (what the app may show as decision-grade)
A stat is decision-grade in a snapshot only if, on the latest rolling-origin test season,
**all** of the following hold:
- the gap between predicted and realized hit rate has a 95% player-clustered CI containing 0,
  or |gap| ≤ 0.02;
- the Brier skill score against the naive baseline is above 0;
- there are at least 50 players and 1,000 player-games.

A stat that fails is not shown with a probability, or is shown only behind an "experimental"
label. The snapshot carries each stat's gate result and the audit's as-of date.
**Staking (Kelly) stays off** in the MVP. It needs calibrated p **and** a real market price
(ADR-0004), and even then it is fractional (Kelly 1956; Thorp 2006) and gated on the lower
bound of the edge CI.

## Consequences
- The README's "honest negative result" table is replaced by the audited numbers (a
  `/stat-rigor claim` task).
- `calibration.py` gains a correct, tested PIT and scorer. The synthetic tests prove that a
  perfectly specified model scores mean-u ≈ 0.5, so the scorer validates itself.

## Verification
`scripts/calibration_audit.py` (real data) and the hermetic unit tests on synthetic, perfectly
specified models. The gate's thresholds are checked by `scripts/mvp_gate.py`.
