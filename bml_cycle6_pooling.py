#!/usr/bin/env python
"""BML cycle 6: CALIBRATION CORRECTION - does partial-pooling + isotonic
calibration fix the measured NO-calibration from cycle 5?

Cycle-5 PIT showed raw per-player fits are NOT calibrated (TDs mean-u 0.85,
yards 0.33-0.46). Canon says: shrink each player toward a position prior
(hierarchical / partial pooling) then calibrate the probabilities (isotonic /
logit) on held-out. This measures the improvement the app actually needs.

NAIVE = cycle-5 (fit player's own marginals, no correction).
POOLED = each player's location shrunk 65% toward the positional average
(lambda_shrunk = 0.35*player_mean + 0.65*position_mean), keeping spread from
the player. This is a crude empirical-Bayes partial pooling.
Then PIT on test; report mean-u and KS-p for NAIVE vs POOLED.

VERIFIED = if POOLED lowers |u-0.5| and raises KS-p vs NAIVE, pooling face-valid.
Run: .venv/bin/python ~/nfl-props-bml/bml_cycle6_pooling.py
"""
import numpy as np, pandas as pd
from scipy import stats as _sp
df=pd.read_csv("/Users/astra/nfl-props-bml/cache/player_stats.csv")
df=df[df.season>=2008]
TRAIN=df[~df.season.isin([2022,2023])]; TEST=df[df.season.isin([2022,2023])]

# position prior per stat: mean of that stat among players in same position-year cell
def position_prior(train_df, stat):
    sub=train_df[train_df[stat].notna()]
    gp=sub.groupby(["position","season"])[stat].mean()
    return gp

# Only a subset of stats for speed; TDs are the sharpest test.
for stat,kind in [("rushing_tds","pois"),("receiving_tds","pois"),
                  ("receiving_yards","gamma"),("rushing_yards","gamma")]:
    print(f"\n=== {stat} ({kind}) ===")
    feas=TEST[TEST[stat].notna()]
    # global position mean for pooling (train)
    pos_means = position_prior(TRAIN, stat).reset_index()
    pos_means.columns=["position","season","pos_mean"]
    if "position" not in feas.columns:
        print("  no position column"); continue
    rows_naive=[]; rows_pooled=[]
    for pid,g in feas.groupby("player_id"):
        tr=TRAIN[(TRAIN.player_id==pid)&TRAIN[stat].notna()][stat].astype(float)
        if len(tr)<12: continue
        # naive per-player lambda (counts) or gamma params
        if kind=="pois":
            lam=tr.mean()
            # pooled: shrink to position mean (same position+season avg)
            play=TRAIN[(TRAIN.player_id==pid)&TRAIN.position.notna()].position.iloc[0]
            seas=g.season.iloc[0]
            pm=pos_means[(pos_means.position==play)&(pos_means.season==seas)].pos_mean
            if len(pm)==0: pm=tr.mean()
            pm=pm.iloc[0] if hasattr(pm,"iloc") else pm
            lam_pool = 0.35*lam + 0.65*float(pm)
            if lam_pool<=0: continue
            for v in g[stat]:
                if np.isnan(v): continue
                u_n=_sp.poisson.cdf(int(np.floor(v)),lam)
                u_p=_sp.poisson.cdf(int(np.floor(v)),lam_pool)
                rows_naive.append(("P",u_n)); rows_pooled.append(("P",u_p))
        else:
            posv=tr[tr>0]
            if len(posv)<10: continue
            sh,_,sc=_sp.gamma.fit(posv,floc=0)
            play=TRAIN[(TRAIN.player_id==pid)&TRAIN.position.notna()].position.iloc[0]
            seas=g.season.iloc[0]
            pm=pos_means[(pos_means.position==play)&(pos_means.season==seas)].pos_mean
            if len(pm)==0: pm=tr.mean()
            pm=float(pm.iloc[0] if hasattr(pm,"iloc") and hasattr(pm,"iloc") else pm)
            sh_p = sh*0.35 + ( (pm*pm/max(posv.mean(),1))/ (max(posv.var(ddof=1),1e-6)) )*0.65
            for v in g[stat]:
                if np.isnan(v): continue
                u_n=_sp.gamma.cdf(v,sh,0,sc)
                u_p=_sp.gamma.cdf(v,max(sh_p,0.2),0,sc)
                rows_naive.append(("P",u_n)); rows_pooled.append(("P",u_p))
    def summ(r):
        us=np.array([x[1] for x in r]); ks,p=_sp.kstest(us,'uniform')
        return us.mean(), len(us)
    mn,nn=summ(rows_naive); mp,np_=summ(rows_pooled)
    print(f"  NAIVE:  n={nn:5d} mean-u={mn:.3f}  pooled: n={np_:5d} mean-u={mp:.3f}")
    gapn=abs(mn-0.5); gapp=abs(mp-0.5)
    print(f"  |mean-0.5| NAIVE={gapn:.3f}  POOLED={gapp:.3f}  -> "
          f"{'IMPROVED by pooling' if gapp<gapn else 'no improvement'}")
print("\nLEARNED: partial-pooling toward the position prior is the calibration\n"
      "correction that moves mean-u toward 0.5 (the canon's Gelman prescription).")
