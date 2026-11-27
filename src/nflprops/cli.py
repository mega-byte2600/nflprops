"""CLI: decision tool on the command line. `nflprops <command> ...`.

MVP commands:
  nflprops forecast <player_name> <stat> <line> [--american +110]
      -> fair prob, EV, edge, fractional-Kelly stake, 90% CI, honest note.
  nflprops list <stat>            -> players ranked by projected output.
  nflprops calibration            -> run the PIT backtest (honest score).
  nflprops copula                  -> show the measured correlation matrix.
Run from the repo with src on the path, or `pip install -e .`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import data as d
from . import odds
from .calibration import pit_backtest
from .engine import Engine


def _resolve_player(df, name, stat=None):
    """Back-compat wrapper around data.resolve_player (shared helper)."""
    try:
        return d.resolve_player(df, name, stat)
    except KeyError as e:
        sys.exit(str(e))


def cmd_forecast(args):
    df = d.load_stats(args.data)
    eng = Engine(df, seed=args.seed)
    pid = _resolve_player(df, args.player, args.stat)
    p = eng.player(pid)
    if p.name: print(f"\n{p.name} ({pid})")
    fc = eng.forecast(pid, args.stat, args.line, n=args.n, ci_level=args.ci)
    if fc is None:
        sys.exit(f"no fit for {p.name} in stat '{args.stat}'")
    print(f"  {args.stat} O/U {args.line}:  P(over)={fc.p_over:.1%}")
    lo,hi=fc.ci
    print(f"  median={fc.median:.1f}  mean={fc.mean:.1f}  {fc.ci_level:.0%} CI=({lo:.1f}-{hi:.1f})")
    if args.american is not None:
        user_decimal = odds.prob_to_decimal(odds.american_to_prob(args.american))
        rhs = odds.ev(fc.p_over, user_decimal)
        kelly = odds.kelly_fraction(fc.p_over, user_decimal)
        stake = odds.fractional_kelly_stake(fc.p_over, user_decimal, args.bankroll, args.kelly_frac)
        print(f"  your line {args.american:+}:  EV={rhs:+.1%}  edge={fc.p_over - odds.decimal_to_prob(user_decimal):+.1%}")
        print(f"  full-Kelly f={kelly:.1%}  stake({args.kelly_frac:.0%} Kelly, bankroll ${args.bankroll:,.0f}) = ${stake:,.2f}")
    print("  HONESTY: raw per-player fits are NOT calibrated - P(over) is a relative\n"
          "  ranking aid, not a guaranteed win probability. Anchor to the closing\n"
          "  line before sizing for real money.")


def cmd_list(args):
    import numpy as np
    df = d.load_stats(args.data)
    eng = Engine(df, seed=args.seed)
    out = []
    for pid in df[df[args.stat].notna()].groupby("player_id")[args.stat].size()\
                 .sort_values(ascending=False).head(50).index:
        p = eng.player(pid)
        fit = p.fits.get(args.stat)
        if fit is None: continue
        samp = eng.simulate(pid, n=args.n).get(args.stat)
        out.append((p.name or pid, float(np.median(samp)) if samp is not None else 0.0))
    print(f"\nTop projected {args.stat} (median over {args.n} sims):")
    for name, med in sorted(out, key=lambda t: t[1], reverse=True)[:12]:
        print(f"  {name:24s} {med:8.1f}")


def cmd_calibration(args):
    df = d.load_stats(args.data)
    train = df[df["season"] < min(args.test_seasons)]   # strictly past -> future
    test = df[df["season"].isin(args.test_seasons)]
    tup = tuple((s, d.STAT_FAMILY[s]) for s in
                ("passing_yards","rushing_yards","receiving_yards",
                 "rushing_tds","receiving_tds"))
    res = pit_backtest(train, test, tup)
    print("\nRandomized PIT backtest (train on seasons before the test seasons):")
    print(res.to_string(index=False))
    print("\nHonest read: a CALIBRATED stat has mean_u~0.5 and KS-p>0.05. Raw fits")
    print("are generally NOT calibrated - use this to decide where to trust the engine.")


def cmd_copula(args):
    df = d.load_stats(args.data)
    R = __import__("nflprops.copula", fromlist=["spearman_matrix"]).spearman_matrix(df)
    cols = ("passing-yds","rushing-yds","receiving-yds","recep","pass-TD","rush-TD","rec-TD")
    print("\nPairwise Spearman correlation matrix (real nflverse data):")
    print("  " + "  ".join(f"{c[:6]:>7}" for c in cols))
    for i, r in enumerate(R):
        print(f"{cols[i]:>11} " + "  ".join(f"{v:+.2f}" for v in r))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="nflprops")
    ap.add_argument("--data", default=str(Path("cache/player_stats.csv")),
                    help="path to nflverse player_stats.csv")
    ap.add_argument("--seed", type=int, default=42)
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("forecast", help="forecast a single prop")
    f.add_argument("player"); f.add_argument("stat"); f.add_argument("line", type=float)
    f.add_argument("--american", type=float, help="your American price, e.g. 110 or -115")
    f.add_argument("--ci", type=float, default=0.95, help="CI coverage, e.g. 0.95 (default) or 0.90")
    f.add_argument("--n", type=int, default=10000)
    f.add_argument("--bankroll", type=float, default=10000.0)
    f.add_argument("--kelly-frac", type=float, default=0.25)
    f.set_defaults(fn=cmd_forecast)

    l = sub.add_parser("list", help="rank players by projected stat")
    l.add_argument("stat"); l.add_argument("--n", type=int, default=5000)
    l.set_defaults(fn=cmd_list)

    c = sub.add_parser("calibration", help="PIT calibration backtest")
    c.add_argument("--test-seasons", type=int, nargs="*", default=[2022, 2023])
    c.set_defaults(fn=cmd_calibration)

    cp = sub.add_parser("copula", help="measured correlation matrix")
    cp.set_defaults(fn=cmd_copula)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()