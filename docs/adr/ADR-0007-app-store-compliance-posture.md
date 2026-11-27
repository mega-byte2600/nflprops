# ADR-0007: App Store and content compliance posture

Status: Proposed (2026-11-27). Re-verify each point against Apple's current App Review
Guidelines and App Store Connect help before the first external TestFlight build; Apple
revises them often.

## Decision
1. **Information only, no real-money gaming.** The app takes no wagers, deposits or entries,
   and links to no sportsbook. The App Review Guidelines' licensing requirements for
   real-money gaming (section 5.3) therefore do not apply. The review notes state this
   explicitly.
2. **Age rating.** Answer the questionnaire truthfully for gambling-related content; expect
   the highest age band. Do not under-declare.
3. **Copy rules.** No "lock", "guaranteed", "can't lose", "risk-free" or "sure thing". Every
   probability is labelled as a model estimate. Responsible-gambling resources (1-800-GAMBLER)
   are on the method screen. A copy lint enforces the banned words (`mvp_gate.py`).
4. **Data and IP.** nflverse data is CC-BY-4.0, attributed in-app. No NFL or team logos, marks
   or official imagery; player names appear as factual references only.
5. **Privacy.** No tracking, no third-party SDKs, and no personal data collected. The privacy
   manifest declares any required-reason APIs; the App Privacy answer is "Data Not Collected".
6. **TestFlight.** Internal testing (team members) needs no Beta App Review; external testing
   does. Start internal.

## Verification
`mvp_gate.py` checks the banned-copy lint, the attribution string, the responsible-gambling
string and the privacy manifest. The owner confirms the age-rating answers and the review notes
at upload.
