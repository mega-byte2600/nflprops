---
name: ios-ux
description: Evidence-based iPhone UI/UX for Prop Desk - layout, flow, uncertainty visualisation, accessibility and usability testing, grounded in Apple's HIG, Nielsen's heuristics, WCAG 2.2 and peer-reviewed research on communicating probability. Use for any screen, flow, copy or chart in ios/PropDesk, before TestFlight builds, and to plan tester rounds. Modes - design <screen>, review <PR>, test.
---

# ios-ux: state-of-the-art, evidence-based iPhone UX

The governing decision is `docs/adr/ADR-0008-ux-information-architecture-and-flows.md`; read
it first. ADR-0007 (compliance) and ADR-0005 (MVP scope) bound what can be designed.

## The evidence base (cite it in PRs; do not invent new rules)
| Area | Source | Rule it gives us |
|---|---|---|
| Platform conventions | Apple Human Interface Guidelines (re-check the current version) | Tab bar for peers, push for depth; Dynamic Type; SF Symbols; 44×44 pt targets; dark mode |
| Usability | Nielsen's 10 heuristics (1994) | Visibility of status, match with the real world, recognition over recall, error prevention |
| Accessibility | WCAG 2.2 AA | Text 4.5:1, non-text 3:1, never colour alone (1.4.1), targets, labels |
| Probability for lay users | Gigerenzer & Hoffrage (1995) | Natural frequencies ("9 in 20") lead; percentages second |
| Uncertainty on mobile | Kay et al. (CHI 2016); Fernandes et al. (CHI 2018) | Quantile dotplots beat intervals and densities for decisions |
| Communicating risk | Spiegelhalter, Pearson & Short (2011), *Science* 333:1393 | Show the distribution, state the limits, keep framing neutral |
| Choice and attention | Hick–Hyman law; Fitts (1954) | Few top-level choices; large, close targets for frequent actions |
| Measuring it | Brooke (1996) SUS; Nielsen (2000) 5-user rounds | SUS ≥ 75, task success ≥ 90%, iterate in small rounds |

## Non-negotiables for this app
1. The answer comes first, as a natural frequency. The chart is a 20-dot quantile dotplot
   with the line marked.
2. No probability-sorted lists, no "best bets", no win/loss colours, no streaks or nudges.
3. Freshness and the line source are always visible. Every state (loading, empty, offline,
   stale, signature failure, unknown schema) is designed.
4. Dynamic Type works at the largest accessibility size with no truncation of the answer;
   VoiceOver reads each row as one sentence; nothing depends on colour alone.
5. Standard SwiftUI and HIG components first (`TabView`, `NavigationStack`, `List`,
   `.searchable`, Swift Charts). Custom controls need a stated reason.

## Modes

### `design <screen>`
1. State the user's question for the screen in one sentence, and the single answer the
   screen gives.
2. Write a layout spec top to bottom (region → content → component), the states, the
   VoiceOver strings and the Dynamic Type behaviour.
3. Map every element to a row of the evidence table. Anything that maps to none is cut.
4. Implement it with SwiftUI previews for each state and size (default, AX5, dark).

### `review <PR>` (a heuristic evaluation, scored)
Score each screen 0–4 on Nielsen's 10 heuristics, plus the five non-negotiables, using the
CI screenshots (default and AX5, light and dark). Report a table: issue | heuristic or rule |
severity (Nielsen 0–4) | fix. Severity 3–4 blocks the PR. Run the accessibility audit test
and paste its result.

### `test` (a usability round with TestFlight testers)
Produce the round plan: 5 testers; 3 tasks (find a player's prop and say which way the model
leans; explain what "9 in 20" means; find when the data was updated); success criteria; the
SUS questionnaire; and a one-page findings template. After the round: the top 3 issues
become backlog items with the evidence attached.

## Output
A short table and a verdict, with evidence-table references. VERIFIED means a measured
result (tests, audit, SUS); VALIDATED means it meets the owner's expectations.
