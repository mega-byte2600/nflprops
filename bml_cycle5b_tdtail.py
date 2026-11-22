import numpy as np, pandas as pd
from scipy import stats as _sp
from scipy.special import comb
df=pd.read_csv("/Users/astra/nfl-props-bml/cache/player_stats.csv")
df=df[df.season>=2008]
TT=df[df.season.isin([2022,2023])]
for stat in ["receiving_tds","rushing_tds"]:
    acts=TT[TT[stat].notna()][stat]
    acts=acts[acts>0]
    mu=acts.mean(); var=acts.var(ddof=1); disp=var/mu
    po2=1-_sp.poisson.cdf(1,mu); ac2=float((acts>=2).mean())
    po3=1-_sp.poisson.cdf(2,mu); ac3=float((acts>=3).mean())
    print(f"\n{stat}: n={len(acts)} mean={mu:.3f} var={var:.3f} disp(active)={disp:.3f}")
    print(f"  Poisson P(>=2)={po2:.3f} vs actual {ac2:.3f}   P(>=3)={po3:.3f} vs actual {ac3:.3f}")
    def nbpmf(k,r,p): return comb(k+r-1,k)*(p**k)*((1-p)**r)
    p=mu/var; r=mu*p/(1-p) if var>mu and p<1 else None
    if r and r>0 and 0<p<1:
        nb2=1-sum(nbpmf(k,r,p) for k in range(2)); nb3=1-sum(nbpmf(k,r,p) for k in range(3))
        print(f"  NB(r={r:.2f},p={p:.3f}) P(>=2)={nb2:.3f} P(>=3)={nb3:.3f}  <-- NB tracks actual tail better?")
print("\n=> if actual P(>=2/3) EXCEEDS Poisson but NB tracks it, TDs need NB (tail-thick),")
print("   even though median dispersion is ~1.0 at the mean. Prop lines price the TAIL.")
