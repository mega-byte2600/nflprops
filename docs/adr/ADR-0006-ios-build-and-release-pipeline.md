# ADR-0006: iOS build verification in CI; the owner archives and uploads

Status: Proposed (2026-11-27)

## Context
Agents run in Linux containers and the dev Mac has only Command Line Tools, so nothing has ever
compiled the Swift code. As of 2026-11-27 the app would also launch to an error screen:
`project.yml` declares no resources (the bundled snapshot is never copied into the app), and
there is no asset catalog, no app icon (App Store Connect rejects an upload without one), no
privacy manifest and no test target.

## Decision
1. **CI on `macos-latest` runs on every PR touching `ios/`** (free for public repos):
   `brew install xcodegen` → `xcodegen generate` →
   `xcodebuild build test -scheme PropDesk -destination 'platform=iOS Simulator,name=<available iPhone>'`.
   It builds unsigned (`CODE_SIGNING_ALLOWED=NO`). This makes the iOS work VERIFIED-by-build.
2. `project.yml` declares the resources (`Assets.xcassets` with `AppIcon`, a bundled signed
   snapshot JSON, `PrivacyInfo.xcprivacy`) and a `PropDeskTests` XCTest target.
3. **Archive and upload stay with the owner** on an Xcode-equipped Mac
   (`ios/TestFlight_RUNBOOK.md`). Automating upload later (App Store Connect API key as a GitHub
   secret plus `xcodebuild -exportArchive`) is a separate owner decision.
4. Every TestFlight upload bumps `CURRENT_PROJECT_VERSION`; `MARKETING_VERSION` stays 0.1.x
   until the MVP is validated.

## Verification
The CI job is green on `main`, and `mvp_gate.py` checks the `project.yml` resources, the test
target, the icon and the privacy manifest.
