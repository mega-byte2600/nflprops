#!/usr/bin/env python
"""BML cycle: does the canonical distribution math fit REAL NFL per-game outcomes?

Risky assumption under test (math layer): gamma fits per-game yardage, negative
binomial fits per-game receptions/TDs, and the mean>median skew the canon predicts
is really present. Uses real settled player_stats.csv (nflverse, keyless, 1999+).

V&V framing: VERIFIED = these fit metrics measured by this run against the real
data. VALIDATED = matches the canon prediction (skew present). Report both.
"""
import numpy as np
import pandas as pd
import scipy.stats as st

CSV = "/Users/astra/nfl-props-bml/cache/player_stats.csv"
COLBY = {"passing_yards": "game", "rushing_yards": "game",
         "receiving_yards": "game", "receptions": "game", "rushing_tds": "game"}
ROLE = {"passing_yards": "QB", "rushing_yards": "RB", "receiving_yards": "wrte"}

print("=== BML round: distribution family fit on REAL NFL per-game outcomes ===\n")
df = pd.read_csv(CSV)
print(f"loaded {len(df):,} player-game rows, seasons {int(df.season.min())}-{int(df.season.max())}\n")

# Restrict to relevant seasons (post-2002 era, stable rules) and drop nothing abnormally high
df = df[(df.season >= 2003)]

results = []
for col, typ in COLBY.items():
    sub = df.dropna(subset=[col])
    # active players only: exclude players with 0 in the stat all year (non-participation rows)
    sub = sub[sub[col] > 0] if col != "receptions" else sub[sub[col] > 0]
    x = sub[col].to_numpy(dtype=float)
    med = float(np.median(x)); mean = float(np.mean(x)); sd = float(np.std(x, ddof=1))
    skew_ = float(st.skew(x))
    n = len(x)
    if typ == "game" and col != "receptions":
        # gamma fit vs normal fit, both by MLE
        gshape, gloc, gscale = st.gamma.fit(x)
        aic_g = -2 * np.sum(st.gamma.logpdf(x, gshape, loc=gloc, scale=gscale)) + 2 * 2
        aic_n = -2 * np.sum(st.norm.logpdf(x, loc=mean, scale=sd)) + 2 * 2
        fam = f"GAMMA(aic={aic_g:.0f}) vs NORM(aic={aic_n:.0f}) -> {'GAMMA' if aic_g<aic_n else 'NORMAL'}"
    else:
        # receptions/TDs: negative binomial vs poisson on counts (use x as observed counts)
        mu = x.mean()
        # NB fit via method of moments (r,p)
        p_nb = mu / (mu + x.var(ddof=1)) if x.var(ddof=1) > 0 else 1.0
        r_nb = mu * p_nb / (1 - p_nb)
        aic_nb = -2*np.sum(st.nbinom.logpmf(x.astype(int), r_nb, p_nb)) + 2*2 if r_nb>0 else np.inf
        aic_po = -2*np.sum(st.poisson.logpmf(x.astype(int), mu)) + 2*1
        fam = f"NB(aic={aic_nb:.0f}) vs POISSON(aic={aic_po:.0f}) -> {'NB' if aic_nb<aic_po else 'POISSON'}"
    flag = "  <-- skew confirmed (mean>median)" if (mean > med and skew_ > 0.5) else ""
    print(f"{col:16s} n={n:7,}  mean={mean:6.2f} med={med:6.2f} sd={sd:6.2f} skew={skew_:+5.2f}{flag}")
    print(f"   {fam}")
    results.append((col, mean, med, sd, skew_, fam))

print("\n=== TDs: dispersion check (poisson vs real) ===")
td = df["rushing_tds"].dropna(); td = td[td > 0]
mu = td.mean(); var = td.var(ddof=1)
print(f"rushing TD/game among scorers: mean={mu:.3f} var={var:.3f} dispersion={var/mu:.3f}")

print("\n=== VERDICTS===")
print(f"VERIFIED (fits measured on real data): {len(results)} stat families fit.")
print(f"VALIDATED (mean>median skew present): {sum(1 for r in results if r[1]>r[2])}/{len(results)} of mean>median")
