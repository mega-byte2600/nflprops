# BML loop history for nflprops

Build-Measure-Learn records. Every number below was MEASURED on real nflverse
data (33 MB `player_stats.csv`, 1999-2024, ~134K player-games) in the working
dir. Reproduce with the scripts referenced. The BML discipline caught real
errors in the canonical literature; trust the measurement, not the canon.

## Cycle 1 — which distribution family fits each stat? (the risky assumption)

Tested: "canon says gamma fits yardage, negative-binomial for counts."
`bml_cycle1_distributions.py` fit gamma vs normal on real per-game values.

- passing_yards: mean 207.6 < median 216.0, skew **-0.18** → NORMAL fits best.
  **This CORRECTS the canon** ("gamma for passing" is wrong — passing is mildly
  left-skew).
- rushing_yards: mean 32.7 vs med 19, skew **+1.72** → GAMMA (validated).
- receiving_yards: mean 34.9 vs med 25, skew **+1.66** → GAMMA (validated).

Learn: family depends on the stat. Do not blanket-apply gamma.

## Cycle 2 — per-player counts: NB vs Poisson? (closes cycle-1 open question)

`bml_cycle2_per_player_counts.py` fit NB vs Poisson PER PLAYER (zeros kept,
method-of-moments NB, min 8 games).

| stat | players | NB | POISSON | median disp | % overdisp(>1.15) |
|---|---|---|---|---|---|
| receptions | 2034 | 723 | 1311 | 1.202 | 54% |
| rushing_tds | 884 | 58 | 826 | 1.000 | 16% |
| receiving_tds | 1566 | 45 | 1521 | 0.968 | 10% |
| passing_tds | 322 | 24 | 298 | 1.000 | 20% |

Learn: TDs are Poisson-like per player (median dispersion ~1.0); receptions are
split (NB for the ~54% overdispersed, Poisson for the rest). Fits per-player by
dispersion, never one league-wide family.

## Cycle 3 — real Monte Carlo engine (verified)

`bml_cycle3_simulation_engine.py`: per-player Monte Carlo with the corrected
families + zero-inflation (gamma/normal reject 0-yard games → fit x>0, gate by
P(>0)). Verified distinct per-player profiles (Jefferson rec mean 95.7/med 85
CI 27-196; Taylor rush 90/82 CI 22-184; Brady pass 274/274 CI 146-402); CI
width shrinks with N (5000 → 171.8, 50000 → 170.5). Also proved the discrete-
event data layer (nflverse PBP 2023+2024 → 49,665-play CSV, all sim fields).

## Cycle 4 — Gaussian copula wired (correctness audit gap closed)

`bml_cycle4_copula.py`: pairwise Spearman matrix on the same data, PSD-
projected, MVN → normal-CDF → per-marginal ppf. Measured anchors:
receiving↔receptions **+0.81**; passing↔receptions **-0.50**; rush↔rush_TD
**+0.28**; receiving↔rec_TD +0.26; passing↔pass_TD +0.43. Verified sampled
corr(recep, rec_yds)=0.786 vs target 0.81.

## Cycle 5 — calibration backtest: the honest negative

`bml_cycle5c_calibrate_full.py`: leakage-free PIT (train < 2022, test 2022-23).
**Raw per-player fits are NOT calibrated** (see the table in the README):
TDs mean-u ~0.76-0.85, yards 0.34-0.46, KS-p < 0.0001 everywhere. Also confirmed
active-game TD counts are strongly peaked at 1 (disp 0.12); Poisson overstates
the multi-TD tail (P(≥2) 0.31 vs actual 0.11). This is the key honesty result
and the reason the engine reports calibration rather than claiming it.

## Cycle 6 — partial-pooling is HONESTLY MIXED

`bml_cycle6_pooling.py` (empirical-Bayes, 0.35*player + 0.65*position prior):

| stat | \|mean-0.5\| naive | pooled | verdict |
|---|---|---|---|
| rushing_yards | 0.169 | 0.057 | IMPROVED |
| receiving_yards | 0.101 | 0.171 | WORSE (overshrunk) |
| rushing_tds | 0.350 | 0.350 | no move |
| receiving_tds | 0.349 | 0.349 | no move |

Learn: pooling is not a silver bullet. TDs need a hurdle/zero-one-inflated
shape (structural, not a location-shrinkage problem); the strongest calibrator
remains the closing market line (Princeton thesis: market features dominate).

## Standing method

- Never self-certify: heavy/mathy work is independently peer-reviewed
  (delegate graders can't write files; fixes are applied and verified on disk).
- VERIFIED = measured by a command / settled outcome. VALIDATED = matches user
  expectation. Label which.
- Real data only; synthetic is test fixtures, not evidence.
- Report wins AND losses, including the measured negatives above.

## Files

- `bml_cycle1_distributions.py` … `bml_cycle6_pooling.py` — the measured loop
- `src/nflprops/` — the cleaned-up package (engine, copula, etc.)
- `cache/` — keyless data cache (not committed; nflverse license)
- `odds_ingestor.py` — keyed odds scaffold (gated on a provider key)