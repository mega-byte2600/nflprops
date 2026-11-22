#!/usr/bin/env python
"""BML cycle 2: PER-PLAYER receptions & TDs — NB vs Poisson (resolve cycle-1 open question).

Cycle 1 pooled cross-player AIC favored Poisson but was not a per-player test.
This fits NB vs Poisson for EACH player's own game-by-game count series
(INCLUDING zero-count games, which cycle 1 wrongly dropped for TDs), then
aggregates. Also reports dispersion (var/mean) per player and per stat.

V&V: VERIFIED = measured by this command on real nflverse data; VALIDATED =
conclusion matches or rejects the canon's 'NB for counts' claim.
"""
import numpy as np, pandas as pd, scipy.stats as st

CSV = "/Users/astra/nfl-props-bml/cache/player_stats.csv"
df = pd.read_csv(CSV)
df = df[df.season >= 2003]

def nb_mom(x):
    """Method-of-moments negative binomial (r,p) from a sample. Return None if underdispersed."""
    mu = x.mean(); var = x.var(ddof=1)
    if var <= mu + 1e-9 or mu <= 0:
        return None  # underdispersed -> NB degenerate toward Poisson
    p = mu / var
    r = mu * p / (1 - p)
    if r <= 0 or p <= 0 or p >= 1:
        return None
    return r, p

# Player-game count series per stat, INCLUDING zeros. A row is a player's game
# appearance; counts already include 0 (verified in cycle 1 head).
def per_player_pick(stat, min_games=8):
    sub = df[df[stat].notna()][["player_id", "week", stat]]
    # one row per player-game
    stats = sub.groupby("player_id")[stat].apply(lambda g: g.to_numpy(dtype=float))
    rows = []
    for pid, x in stats.items():
        x = np.asarray(x, dtype=float)
        if len(x) < min_games: continue
        mu = x.mean()
        if mu <= 0: continue
        # Dispersion (>1 => overdispersed => NB favored)
        var = x.var(ddof=1); disp = var / mu if var > 0 else 1.0
        xi = x.astype(int)
        # Poisson LL with lambda=mu; AIC
        ll_po = np.sum(st.poisson.logpmf(xi, mu)); aic_po = -2 * ll_po + 2
        mom = nb_mom(x)
        if mom is not None:
            r_nb, p_nb = mom
            ll_nb = np.sum(st.nbinom.logpmf(xi, r_nb, p_nb)); aic_nb = -2 * ll_nb + 4
        else:
            aic_nb = np.inf
        win = "NB" if aic_nb < aic_po else ("POISSON" if aic_po < aic_nb else "TIE")
        rows.append((pid, len(x), mu, var, disp, aic_po, aic_nb, win))
    return pd.DataFrame(rows, columns=["player_id","n","mean","var","disp","aic_po","aic_nb","win"])

for stat in ["receptions", "rushing_tds", "receiving_tds", "passing_tds"]:
    res = per_player_pick(stat)
    if res.empty:
        print(f"{stat:14s}: no qualifying players"); continue
    wins_nb = (res.win == "NB").sum()
    wins_po = (res.win == "POISSON").sum()
    over = float((res.disp > 1.15).mean())
    print(f"\n=== {stat} ({len(res)} players, >=8 games each, zeros included) ===")
    print(f"  per-player AIC winners: NB={wins_nb}  POISSON={wins_po}  ties={(res.win=='TIE').sum()}")
    print(f"  median dispersion var/mean = {res.disp.median():.3f}  frac overdispersed(>1.15)={over:.0%}")
    print(f"  median n per player = {int(res.n.median())}")