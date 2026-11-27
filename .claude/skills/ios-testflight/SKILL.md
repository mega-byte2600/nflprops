---
name: ios-testflight
description: iOS build and TestFlight readiness for Prop Desk. Use for any change under ios/PropDesk, any project.yml change, and before handing a build to the owner for upload. Modes: check (what blocks TestFlight now), release (prepare a release candidate and upload notes). Agents verify builds in macOS CI; only the owner archives, signs and uploads.
---

# ios-testflight: build-verified, review-ready, owner-uploaded

Governing decisions: ADR-0005 (MVP scope), ADR-0006 (pipeline), ADR-0007 (compliance).
Owner runbook: `ios/TestFlight_RUNBOOK.md`.

## What an agent can and cannot do
- **Can:** edit Swift and `project.yml`; run `xcodegen` and `xcodebuild build test` in the
  macOS CI job; read CI logs; write release notes.
- **Cannot:** sign, archive or upload; touch certificates, `.p8`/`.p12` files or provisioning
  profiles; answer App Store Connect questionnaires. Those belong to the owner.
- From a Linux container, iOS changes are VERIFIED only once the macOS CI job is green. Never
  claim "builds" from reading code.

## `check`
Run `python scripts/mvp_gate.py` and report the iOS rows, plus the latest macOS CI conclusion.
The blockers to look for:
1. `project.yml` declares resources: `Assets.xcassets` (with a 1024×1024 `AppIcon`), the
   bundled signed snapshot, and `PrivacyInfo.xcprivacy`.
2. There is a `PropDeskTests` target, and XCTest decodes and verifies the golden snapshot.
3. The app shows the data as-of date, the nflverse CC-BY-4.0 attribution and
   responsible-gambling resources, and has no banned copy (ADR-0007).
4. Signature verification is Ed25519 with an embedded **public** key only (ADR-0002).
5. Layout works with Dynamic Type at the largest accessibility size, VoiceOver labels exist
   on the chart and probabilities, and a dark-mode check passes.

## `release`
1. `mvp_gate.py` exits 0, and both CI jobs are green on the release commit.
2. Bump `CURRENT_PROJECT_VERSION` in `project.yml`; keep `MARKETING_VERSION` at 0.1.x.
3. Write `ios/RELEASE_NOTES.md`: what to test, known limits (which stats are experimental),
   and the TestFlight "What to Test" text.
4. Write the App Review notes: information only, no wagering, no sportsbook links, data
   source and licence.
5. Hand off to the owner with the exact runbook steps. Internal testing first (no Beta App
   Review).
