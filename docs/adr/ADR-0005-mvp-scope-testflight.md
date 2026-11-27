# ADR-0005: MVP scope for TestFlight

Status: Proposed (2026-11-27)

## Riskiest assumption the MVP tests
That people find **calibrated, honestly labelled prop distributions** useful enough to come
back each week. The MVP is the smallest build that tests this.

## In scope
1. **Prop list.** Players and stats in a snapshot with P(over) **only for gate-passing stats**
   (ADR-0003), the line and its source label (ADR-0004), the median, and an 80% interval.
   Sorted by player or stat, **not** by probability; ranking by P(over) is meaningless without
   a market.
2. **Prop detail.** A distribution chart (quantiles), how often similar predictions came true
   (from the audit), data as-of, and the honest limits panel.
3. **Method and limits screen.** A plain-language method summary, calibration results per stat,
   nflverse CC-BY-4.0 attribution, and responsible-gambling resources (1-800-GAMBLER).
4. **Data freshness.** The snapshot as-of date is always visible; a stale snapshot is labelled.
5. **Offline-first** bundled snapshot plus fetch of a newer signed one (ADR-0001, ADR-0002).
6. A TestFlight feedback prompt: one question, "Was this useful this week?".

## Out of scope for the MVP (explicitly)
Accounts and login, payments or in-app purchase, bet placement, sportsbook links, Kelly stakes,
push notifications, live in-game updates, social features, and team logos or NFL marks.

## Definition of done
`scripts/mvp_gate.py` exits 0, CI builds the app on a macOS runner, and the owner has uploaded
build 1 to TestFlight internal testing.
