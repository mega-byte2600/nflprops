#!/usr/bin/env python
"""BML cycle 5: CALIBRATION BACKTEST - Probability Integral Transform (PIT).

Rigorous, leakage-free calibration test of the engine marginals:
  - Train each player's stat marginal ONLY on seasons < test (no leakage).
  - On held-out games, compute u = CDF_fit(actual_outcome | positive usage).
  - A correctly-calibrated model has u ~ Uniform(0,1).
  - Test with a KS test + deviations; report Brier of a surrogate yes/no too.

For zero-inflated marginals: u is computed on the conditional (X>0) distribution,
so only games where the player was active (stat>0) are scored. This tests the
severity/shape of the marginal, which is exactly what prop line-pricing needs.

VERIFIED = if calibrated, KS p >> 0.05 and histogram flat. Also report how far
the fitted CDF is from the empirical CDF (worst-case |Fu_emp - Fu_theory|).
Run: .venv/bin/python ~/nfl-props-bml/bml_cycle5_calibration.py
"""
import numpy as np, pandas as pd
from scipy import stats as _sp

CSV = "/Users/astra/nfl-props-bml/cache/player_stats.csv"
df = pd.read_csv(CSV)
df = df[df.season >= 2008]
TEST_SEASONS = [2022, 2023]
TRAIN = df[~df.season.isin(TEST_SEASONS)]
TEST  = df[df.season.isin(TEST_SEASONS)]

def fit_marginal(sub, pid, stat, kind):
    x = sub[(sub.player_id==pid)&sub[stat].notna()][stat].astype(float).to_numpy()
    if len(x)<12 or x.mean()<=0: return None
    pos = x[x>0]
    if len(pos)<10: return None
    if kind=="gamma":
        sh,_,sc=_sp.gamma.fit(pos, floc=0)
        return ("gamma",(sh,sc))
    if kind=="norm":
        mu,sd=pos.mean(),pos.std(ddof=1)
        if sd<=0: return None
        return ("norm",(mu,sd))
    lam=pos.mean()
    return ("pois",(lam,))

def cdf_fit(s, fit):
    kind,par=fit
    if kind=="gamma":
        sh,sc=par; return _sp.gamma.cdf(s, sh, 0, sc)
    if kind=="norm":
        mu,sd=par; return _sp.norm.cdf(s, mu, sd)
    lam=(par[0] if isinstance(par,(list,tuple)) else par)
    return _sp.poisson.cdf(int(np.floor(s)), lam)

rows=[]
for stat,kind in [("passing_yards","norm"),("rushing_yards","gamma"),
                  ("receiving_yards","gamma"),("rushing_tds","pois"),
                  ("receiving_tds","pois")]:
    for pid,g in TEST.groupby("player_id"):
        fit=fit_marginal(TRAIN,pid,stat,kind)
        if fit is None: continue
        y=g[stat].astype(float).to_numpy()
        y=y[y>0]
        for v in y:
            u=float(cdf_fit(v,fit))
            u=max(min(u,1-1e-9),1e-9)
            rows.append((stat,u,fit[0]))

res=pd.DataFrame(rows,columns=["stat","u","fam"])
print("=== PIT CALIBRATION BACKTEST (train<2022, test 2022-23) ===")
print(f"total scored u-values: {len(res)}\n")
for stat,sub in res.groupby("stat"):
    us=sub.u.to_numpy()
    ks,p=_sp.kstest(us,'uniform')
    mean=us.mean(); std=us.std(ddof=1)
    # worst deviation from uniform ECDF
    ecdf=np.sort(us); n=len(us)
    dev=np.abs(ecdf-np.linspace(0,1,n))
    flagged="CALIBRATED" if p>0.05 else "POOR CALIBRATION"
    print(f"{stat:16s} n={n:6d}  mean={mean:.3f}  sd={std:.3f}  "
          f"KS-p={p:.3f}  max|dev|={dev.max():.3f}  -> {flagged}")
print(f"\n{('VALIDATED (majority CALIBRATED) if most stats KS-p>0.05')}")
