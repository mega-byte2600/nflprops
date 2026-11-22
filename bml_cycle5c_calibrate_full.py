#!/usr/bin/env python
"""BML cycle 5c: CORRECTED calibration - PIT per-player using FULL distributions
(zeros included), which is how a TD line (O/U 0.5, 1.5, 2.5) is actually priced.
Previous cycle-5 conditioned on positive games and found "poor calibration";
that was partly an artifact of conditioning. This scores the distribution the
line actually prices.

For each player: fit marginal on train seasons (<2022) using ALL games
(zeros kept). For each held-out game value v (positive OR zero), u=CDF_fit(v).
Pool u. Calibrated => u~Uniform(0,1) (KS p>0.05, mean~0.5).
The zero-heavy nature is handled by including u=0 naturally for zero games.
"""
import numpy as np, pandas as pd
from scipy import stats as _sp
df=pd.read_csv("/Users/astra/nfl-props-bml/cache/player_stats.csv")
df=df[df.season>=2008]
TRAIN=df[~df.season.isin([2022,2023])]; TEST=df[df.season.isin([2022,2023])]

def fit_all(sub,pid,stat,kind):
    x=sub[(sub.player_id==pid)&sub[stat].notna()][stat].astype(float).to_numpy()
    if len(x)<12 or x.mean()<=0: return None
    if kind=="gamma":
        pos=x[x>0]
        if len(pos)<10: return None
        sh,_,sc=_sp.gamma.fit(pos,floc=0)
        return ("gamma_z","full",(sh,sc),pos.mean(),x)  # P(>0) implicit via zeros in CDF
    if kind=="norm":
        pos=x[x>0]
        if len(pos)<10: return None
        mu,sd=pos.mean(),pos.std(ddof=1)
        if sd<=0: return None
        return ("norm_z","full",(mu,sd),pos.mean(),x)
    lam=x.mean()   # counts: fit on ALL games (zeros included) -> correct for line pricing
    return ("pois","full",(lam,),None,x) if lam>0 else None

def cdf_full(v,fit):
    kind,_,par,_,_=fit
    if kind=="gamma_z":
        sh,sc=par; return _sp.gamma.cdf(v,sh,0,sc)
    if kind=="norm_z":
        mu,sd=par; return _sp.norm.cdf(v,mu,sd)
    lam=(par[0] if isinstance(par,(list,tuple)) else par)
    return _sp.poisson.cdf(int(np.floor(v)),lam)

rows=[]
for stat,kind in [("passing_yards","norm"),("rushing_yards","gamma"),
                  ("receiving_yards","gamma"),("rushing_tds","pois"),
                  ("receiving_tds","pois")]:
    for pid,g in TEST.groupby("player_id"):
        fit=fit_all(TRAIN,pid,stat,kind)
        if fit is None: continue
        y=g[stat].astype(float).to_numpy()
        for v in y:
            if np.isnan(v): continue
            u=float(cdf_full(v,fit)); u=max(min(u,1-1e-9),1e-9)
            rows.append((stat,u))

res=pd.DataFrame(rows,columns=["stat","u"])
print("=== CORRECTED PIT (full distribution incl zeros, train<2022, test 2022-23) ===")
print(f"total u-values: {len(res)}\n")
for stat,sub in res.groupby("stat"):
    us=sub.u.to_numpy(); ks,p=_sp.kstest(us,'uniform')
    ecdf=np.sort(us); dev=np.abs(ecdf-np.linspace(0,1,len(us)))
    flag="CALIBRATED" if (p>0.05 and abs(us.mean()-0.5)<0.05) else "POOR"
    print(f"{stat:16s} n={len(us):6d}  mean={us.mean():.3f}  KS-p={p:.4f}  "
          f"max|dev|={dev.max():.3f}  -> {flag}")
