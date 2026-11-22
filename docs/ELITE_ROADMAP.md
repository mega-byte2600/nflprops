# ELITE ROADMAP — done right, little by little

Building the elite betting methodology into nflprops as small, measured,
committed increments (the user's "elite done right little by little"). Each
increment: build → V&V on real play-by-play → commit a working slice. No
big-bang rewrites; the package stays green at every step.

Grounded in the elite-methodology research (Voulgaris/Ewing possession
simulation, NFL syndicate EPA pricing, Sports Insights/syndicate tradecraft)
and the math canon in nfl-prop-prop-betting / nfl-prop-math-canon.

## Progress

| # | Increment | Status | Evidence |
|---|---|---|---|
| 0 | Elite play-by-play data substrate (nflverse pbp 2023-24, 47 cols, EPA/EP/WPA sane) | ✅ done | `cache/pbp_2023_elite.csv` (49,665 plays), `pbp_2024_elite.csv` (49,492); EPA -0.02, EP 1.57, WPA 0.0003 |
| 1 | `elite.py`: neutral-script EPA team ratings + pass-weighted dropback efficiency | ✅ done | pass EPA +0.014 > run EPA -0.027 on 2023; SF/MIA/DET top, NYJ/CAR/NYG worst |
| 2 | Opponent-quality adjustment (defense-strength schedule) | ✅ done | BAL/CLE/NE strong D; opponent-adj bumps IND/LAC/JAX/HOU up, DAL/SF/BAL/NYG down |
| 3 | Team-strength PRIOR on player projections (Gelman partial-pooling) | ✅ done | corr(team rating, team rec-ypg)=0.72 '23 / 0.36 '24; shrinkage falls 0.085→0.019→0.010 as games rise; high-usage players defer to own record (w=0.99) |
| 4 | Possession-level discrete-event simulator (drive=atomic unit, field-stratified) | ✅ done | 15,988 real drives; RAW team 20.8pts/363yds/41.6 total ≈ NFL; rated SF@DAL: 22.0pts/390yds; 90% CI total (25,65). Field-start empirical fix cut 2x scoring inflation |
| 5 | Strike seam: EPA/total gap vs market anchor, CI-gated, honest | ✅ done | SF@DAL: sim 22.3 vs 24.5 → gap -2.2, 90% CI (9.6,38.3) → no-striking-edge (correct: within noise); refuses to invent a market anchor keyless |

## The elite methodology we are implementing (from the research)

1. Price on **play-by-play EPA**, not box scores or final scores. Passing EPA is
   more stable week-to-week and more predictive than rushing EPA → weight
   dropback/pass efficiency above ground efficiency when projecting future
   output.
2. **Neutral-script filtering**: discount garbage-time (win probability outside
   ~20-80% in the first three quarters) — scrub 4th-quarter prevent-defense
   drives where EPA isn't skill.
3. **Opponent-quality adjustment**: raw EPA against a weak schedule overstates
   a team; adjust for opponent strength, especially early in the season.
4. **Simulate the unit of play** (possession/drive → micro-outcomes), run tens
   of thousands of sims, discard outlandish forks — Voulgaris's Ewing model.
   This is why we hold play-by-play, not only player box stats.
5. **Execute sharp-style**: the edge is CLV / line-shopping / speed, never
   "predict the winner." The engine reports value vs the market, not winners.

## Increment 1 — neutral-script EPA team ratings (VERIFIED)

Build: `elite.py` in src/nflprops. Loads pbp, applies neutral-script filter
(wp in [0.20, 0.80] and qtr<=3), computes per-team per-play pass EPA and rush
EPA, and a pass-weighted dropback-efficiency rating with a documented weight.

V&V: VERIFIED = passes against real data below.

## Reproduce

```
nflprops --data cache/player_stats.csv elite-ratings \
    --pbp cache/pbp_2023_elite.csv --season 2023
```
(+ test suite: `python -m pytest tests/test_elite.py -q`)

## Key numbers anchored (recompute from data, do not trust memory)

- Track pass_epa mean vs rush_epa mean; passing EPA should be higher and more
  predictive (research finding). Report the measured delta and stability.
- Report top/bottom teams by both raw and opponent-adjusted rating once Inc 2
  lands; the ranking should be sane (e.g. elite offenses near top).