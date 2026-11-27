# ADR-0004: Market anchor, with real timestamped lines or an "illustrative" label

Status: Proposed (2026-11-27)

## Context
The default snapshot specs hard-code lines (for example "Justin Jefferson receiving yards
70.5"). These are not market lines; they are invented. The app renders them as "Over 70.5"
with no label. The prop-market literature is consistent that closing lines are close to
efficient: the defensible value is pricing against the market (line shopping, CLV), not
predicting better than it.

## Decision
1. Every line shown carries a `line_source` (provider and book) and `line_as_of` (UTC). A line
   without a real source is shown as **"Illustrative line"** and never produces an edge.
2. Edge, EV and fair price are computed only against a **de-vigged** two-sided market (the
   per-book over/under pair, then the median across books; `odds.consensus_fair`). With no
   market, `edge = null` and the app says so.
3. Success is measured by **closing-line value** and calibration over many props, never by
   short-run ROI. The app never shows win/loss records as proof of skill.
4. An odds provider (for example The Odds API) is the owner's decision. The key stays
   server-side (`/harden-datalink`), and the app never sees it.
5. Interim MVP lines are a player's historical median plus a half point, labelled
   "Illustrative line (historical median)", so the probabilities are about something
   reproducible and are not a fake market.

## Verification
Schema fields `line_source` and `line_as_of` are required (`/snapshot-contract`). A test
rejects a snapshot where `edge` is not null but `line_source` is "illustrative".
