#!/usr/bin/env python
"""Odds ingestor scaffold - keyless-first (bml/a). Reads multi-book NFL player
prop odds, de-vigs to a consensus fair price, and caches. Designed so it works
the moment a provider key exists; box-score/outcome layer runs entirely keyless
via nflverse (already verified).

PROVIDER GATE (per track-a probe, Nov 2026):
  - The Odds API : free 500 credits/mo, REST poll, player props + alt lines.
    Requires apiKey. Endpoint: GET /v4/sports/americanfootball_nfl/events/
    ?regions=us&markets=player_pass_yds,player_receptions&oddsFormat=american
  - PropLine      : 119 books+exchanges side-by-side; requires token.
  - EndzoneAPI    : free, prop history + settled; unreachable from this host
    in probe (re-test; was resolving).
  No key is present in this environment, so live fetch is stubbed behind
  load_odds() which MUST be given a provider config. The settled-outcome layer
  (load_box_scores) is NOT stubbed - it runs on nflverse CSV already cached.

Rigor: never fabricate provider output. Until a key exists, this module can
only build the no-vig consensus from an injected odds dict, and REPORTS that
live odds are unavailable rather than inventing them.
"""
import json, os, math, time
from pathlib import Path

CACHE = Path("/Users/astra/nfl-props-bml/cache")

# ---------------------------- provider layer (gated) ---------------------
def get_key(name):
    """Pull a key from env (THE_ODDS_API_KEY etc). Returns None if unset."""
    env = {"odds_api":"THE_ODDS_API_KEY","propline":"PROPLINE_TOKEN",
           "endzone":"ENDZONE_API_KEY"}.get(name)
    if env and os.environ.get(env):
        return os.environ[env]
    return None

def load_odds_json(path):
    """Read a cached JSON odds snapshot. Returns list of prop dicts."""
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text())

# ---------------------------- de-vig math ---------------------------------
def american_to_prob(american):
    if american >= 0:
        return 100.0 / (american + 100)
    return (-american) / (-american + 100)

def devig_proportional(implieds):
    """Multiplicative de-vig: divide each implied by the overround sum."""
    s = sum(implieds)
    if s <= 0: return None
    return [i / s for i in implieds]

def consensus_fair(market_prices, method="proportional"):
    """market_prices: list of candidate implied probabilities (one per book,
    ideally already de-vigged). Returns median (robust consensus) + spread."""
    if not market_prices: return None
    return {"fair_p": float(np_median(market_prices)),
            "n_books": len(market_prices),
            "spread_pt": max(market_prices) - min(market_prices)}

def np_median(v):
    try:
        import numpy as np
        return float(np.median(v))
    except ImportError:
        s = sorted(v); n = len(s)
        return (s[n//2] if n % 2 else 0.5*(s[n//2-1]+s[n//2]))

# ---------------------------- outcome layer (keyless) ---------------------
def load_box_scores():
    """nflverse player_stats.csv (verified keyless). Returns DataFrame."""
    import pandas as pd
    p = CACHE / "player_stats.csv"
    if not p.exists(): return None
    return pd.read_csv(p)

# ---------------------------- CLV / honest-output -------------------------
def evaluate_prop(prop, box_df):
    """Against a settled box-score fact, report CLV (did your fair edge beat
    the line?) - the only defensible skill metric. prop = {name, line, side,
    fair_p, best_book, best_price}."""
    # CLV needs: the settled outcome's implied prob of your side vs your edge.
    # Without live odds this is a scaffold; returns the schema.
    return {"prop": prop.get("name"), "edge_ev": None,
            "needs_odds_key": True,
            "note": "live odds gated; settle CLV once a provider key is wired"}

if __name__ == "__main__":
    print("odds ingestor scaffold")
    print("  box_scores:", "available" if load_box_scores() is not None else "MISSING")
    print("  odds_api_key:", "SET" if get_key("odds_api") else "not set (gated)")
    print("  propline_key:", "SET" if get_key("propline") else "not set (gated)")
    # demo de-vig on a real-style prop line set:
    # e.g. Player passing yards O/U 274.5, three books: -115 / +260(over implied)
    demo = [0.535, 0.520, 0.545]   # three books' implied probs of Over
    print("  demo consensus fair_p(Over):", consensus_fair(demo))