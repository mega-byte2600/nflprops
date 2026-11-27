# ADR-0008: UX information architecture, flows, and how uncertainty is shown

Status: Proposed (2026-11-27). Owner: the iOS engineer and Architect lanes; enforced by
`/ios-ux`.

## Context
The scaffold is a single list sorted by P(over), with a detail screen whose chart is a bar
from the CI low to the CI high. Three evidence problems:
1. **Sorting by P(over) invites a misreading.** A high P(over) at a low line is not value,
   and without a market price the sort order implies a recommendation the model does not make.
2. **Percentages and intervals are poorly understood by lay users.** Natural frequencies
   ("about 3 in 10 games") improve probabilistic reasoning (Gigerenzer & Hoffrage, 1995,
   *Psychological Review* 102:684). On mobile, **quantile dotplots** lead to better
   decisions under uncertainty than intervals or densities (Kay, Kola, Hullman & Munson,
   CHI 2016; Fernandes et al., CHI 2018).
3. Nothing in the flow states data freshness or the limits up front. Visibility of system
   status is the first usability heuristic (Nielsen, 1994).

## Decision: information architecture (three tabs, standard iOS patterns)
Use a `TabView` with three tabs, each a `NavigationStack` (Apple HIG: tab bars for top-level
peers, push navigation for depth).
1. **This Week.** Props grouped by game (kickoff time, then matchup), then by player.
   A row shows the player, stat, line with its source chip ("Illustrative" or the book), the
   median, and "Over in N of 20 similar games". No sort by probability. Experimental stats
   are collapsed under a disclosure row labelled "Experimental".
2. **Search.** Player search (`.searchable`) leading to the player page, which lists all of
   the player's props for the week.
3. **Method.** Plain-language method summary, calibration results per stat (from the audit),
   data as-of, nflverse CC-BY-4.0 attribution, responsible-gambling resources (1-800-GAMBLER),
   and About.

## Decision: the prop detail screen (one question per region, top to bottom)
1. **The answer:** "Over 70.5 receiving yards: about 9 in 20 games (45%)". The natural
   frequency leads, and the percentage is secondary.
2. **The picture:** a 20-dot quantile dotplot of the predictive distribution with the line
   drawn on it; dots right of the line are tinted. One dot means one in 20 outcomes. It must
   work in monochrome, so the line position, not colour alone, carries the meaning
   (WCAG 2.2 SC 1.4.1).
3. **How sure we are:** "Model calibration for receiving yards: predicted 44%, happened 43%
   (2024–26)". Drawn from the audit, so trust is earned with evidence.
4. **Context:** the median, the 80% range, the game's implied team total, data as-of.
5. **Limits:** one short sentence, plus a link to Method. No walls of warning text.

## Decision: interaction and visual rules
- **Apple HIG baseline:** system fonts with Dynamic Type at every size including the
  accessibility sizes; SF Symbols; hit targets of at least 44×44 pt; system colours with
  dark mode; and standard back-swipe and tab behaviour (no custom gestures).
- **Contrast:** at least 4.5:1 for text and 3:1 for chart marks (WCAG 2.2 AA).
- **VoiceOver:** each row and chart has a sentence-level label, for example "Over 70.5
  receiving yards. About 9 in 20 games. Line is illustrative."
- **Freshness:** a status line is always visible on This Week ("Data through week 12 ·
  updated Tue 06:10"); a stale snapshot turns it amber with its age.
- **States:** loading, empty ("No props this week"), offline (last verified snapshot with its
  date), signature-failure, and unknown-schema states are each designed, never blank.
- **No engagement dark patterns:** no streaks, badges, push nudges or "hot pick" styling; no
  red-green win/loss framing. This is a decision aid, and gambling-adjacent products must not
  borrow variable-reward mechanics (ADR-0007).

## Success metrics (measured with TestFlight testers)
- **Comprehension:** at least 80% of testers correctly answer "out of 20 games, how many go
  over?" from the detail screen (a 5-question in-app check, optional).
- **Usability:** a System Usability Scale score of at least 75 (Brooke, 1996; Bangor,
  Kortum & Miller, 2009). Task success of at least 90% on "find Player X's rushing prop and
  say whether the model leans over".
- **Method:** rounds of 5 testers each (Nielsen, 2000), fix, repeat; a heuristic evaluation
  (`/ios-ux review`) before every TestFlight build.

## Verification
XCUITest takes screenshots of each screen at the default size and at the largest
accessibility size, in light and dark mode, as CI artifacts. `/ios-ux review` scores them
against this ADR. An accessibility audit test runs (`XCUIApplication().performAccessibilityAudit()`, iOS 17+).
