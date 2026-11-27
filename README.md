# nflprops — an honest NFL player-prop decision engine

Pricing NFL player props with calibrated probabilities, Monte Carlo with
copula dependence, fractional-Kelly staking, and — critically — an honest
score of whether the model is actually calibrated. Built on free, keyless
[nflverse](https://github.com/nflverse/nflverse-data) data. No API key needed.

> **Read this first.** This is **not** a "beat the house" app and does not
> guarantee winners. The peer-reviewed and open-source record is consistent:
> prop markets are close to efficient at the close, and no strategy has robustly
> beaten a de-vigged market out of sample. The defensible edge is **finding
> value against the market** (line-shopping, CLV), **not** predicting better
> than a Pinnacle/execution calc. Every output in this engine is a probability
> with a confidence interval and an explicit honesty caveat — never a win
> guarantee. Presented as capability, never guaranteed performance.

## What it does (and what it is deliberately NOT)

| Capability | Provided? | Notes |
|---|---|---|
| Per-player marginal distribution fits | ✅ | MEASURED families: gamma (rush/rec yards), normal (pass yards), Poisson TDs, dispersion-gated NB receptions, zero-inflated |
| Correlated prop simulation | ✅ | Gaussian copula over the measured correlation matrix (receiving↔receptions +0.81, etc.) |
| Over/under probability + 90% CI | ✅ | P(stat > line) via Monte Carlo |
| EV / edge / fractional-Kelly stake | ✅ | Standard betting math, worked examples in the tests |
| Factory-calibrated probabilities | ⚠️ | See the honest negative result below — the engine *reports* that raw fits are NOT calibrated; it does not fake calibration |
| Live odds ingest | 🔒 | Gated on a provider key (The Odds API / PropLine). The keyless box-score + settled-history layer works now |
| A guaranteed-money model | ❌ | Deliberately absent. It would be dishonest |

## The honest negative result (why you can trust this engine)

An independent calibration backtest (`nflprops calibration`, leakage-free PIT,
train < 2022, test 2022-23) on real nflverse data shows that **raw per-player
fits are not calibrated**:

| stat | mean-u | KS-p | verdict |
|---|---|---|---|
| passing_yards | 0.458 | 9.9e-05 | poor |
| rushing_yards | 0.341 | ~0 | poor |
| receiving_yards | 0.401 | ~0 | poor |
| rushing_tds | 0.762 | ~0 | poor |
| receiving_tds | 0.780 | ~0 | poor |

A well-calibrated model has mean-u ≈ 0.5. The pattern is systematic: per-player
all-games TDs under-weight the chance of a TD in a given game, and 2-parameter
gamma/normal misplace mass on heavy-tailed, overdispersed yardage. **The engine
tells you this** instead of overclaiming. The fixes the canon prescribes —
hierarchical partial-pooling toward a position prior, isotonic/logit
calibration correction fit on held-out data, and anchoring to the closing
market line (which embeds all of this) — are the honest path, and the measured
mixed result of naive partial-pooling is documented in `docs/BML_LOOP.md`.

## Quickstart

```bash
# 1. (once) fetch keyless nflverse player stats (33 MB)
python - <<'PY'
import nflprops, pathlib
p = nflprops.ensure_cache(pathlib.Path("cache"))
print("cached at", p)
PY

# 2. forecast a prop
nflprops --data cache/player_stats.csv forecast "Justin Jefferson" receiving_yards 100
nflprops --data cache/player_stats.csv forecast "Justin Jefferson" receiving_yards 90 --american +110 --bankroll 10000

# 3. rank players
nflprops --data cache/player_stats.csv list rushing_yards

# 4. run the calibration backtest (the honesty gate)
nflprops --data cache/player_stats.csv calibration

# 5. show the measured correlation matrix
nflprops --data cache/player_stats.csv copula

# 6. run the test suite
python -m pytest tests/ -q
```

Or install: `pip install -e .` (dev deps: `pip install -e .[dev]`).

## Package layout

```
src/nflprops/
  data.py        keyless nflverse ingestion (no auth, no key)
  marginals.py   per-player zero-inflated fits (measured families)
  copula.py      Gaussian copula + measured Spearman correlation matrix
  engine.py      Engine: marginals -> copula -> Monte Carlo -> CI + P(over)
  odds.py        odds conversion, EV, edge, fractional-Kelly, CLV
  calibration.py PIT backtest + isotonic calibration (the honesty gate)
  cli.py         nflprops command-line tool
docs/BML_LOOP.md the measured build-measure-learn history
tests/          unit tests (synthetic data, no download needed)
```

## Why keyless

The MVP runs fully on nflverse box scores (CC-BY-4.0, 1999-present, every stat a
prop prices). Live hydrated odds (The Odds API free tier, PropLine) require a
provider key; the ingest seam in `data.py`/`engine.py` accepts them but nothing
in the package *requires* one to run, and the client never embeds a key.

## Honesty pledge (how this survives V&V)

- Every number in the repo is either reproducible (`pytest`, the reproduce
  commands above) or explicitly marked MEASURED with its source.
- The calibration backtest is wired in and runnable; the skill does not claim
  the model is calibrated — it reports the calibration curve.
- Negative and mixed results (partial-pooling helps some stats, hurts others)
  are documented, not hidden.
- No money-edge claim. Edge is stated relative to the market, never absolute.

## Controlled development

Executable changes follow the incremental lifecycle and human approval gates in
[`docs/SOFTWARE_LIFECYCLE_PLAN.md`](docs/SOFTWARE_LIFECYCLE_PLAN.md). Requirements,
risks, and verification evidence are linked in
[`docs/TRACEABILITY.md`](docs/TRACEABILITY.md); unresolved limitations are kept
visible in [`docs/KNOWN_ANOMALIES.md`](docs/KNOWN_ANOMALIES.md). AI agents may
prepare and verify changes but are not authorized to merge or release them.

## License

MIT. Data: nflverse `player_stats` is CC-BY 4.0.
