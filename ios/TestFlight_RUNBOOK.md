# TestFlight runbook — Prop Desk (NFL)

Faithful, current-Apple-docs path to get the iOS app onto real iPhones via
TestFlight. This runs on a Mac WITH full Xcode.app (this repo's dev Mac only
has Command Line Tools; the iOS target cannot be archive/signed here — that
step is VERIFIED-by-hand not VERIFIED-by-build until Xcode is present).

## Prereqs (once, on an Xcode-equipped Mac)
1. Install full Xcode from the Mac App Store. Verify: `xcodebuild -version`
   prints a real version (not the "command line tools instance" error), and
   `xcrun simctl list devices available` lists iPhones.
2. Have an active Apple Developer Program membership (needed for TestFlight;
   free Apple ID alone cannot distribute).
3. Add your Apple ID: Xcode > Settings > Accounts > "+" > Apple ID. Confirm
   your team appears under the Signing & Capabilities pane when you open the
   project.
4. Install XcodeGen (`brew install xcodegen`) OR open project.yml in Xcode —
   if you have XcodeGen, generate the .xcodeproj:
     cd ios/PropDesk && xcodegen generate

## Generate the snapshot (server-side, keyless) the app reads
The iPhone never holds an odds key. Precompute + sign server-side:
  cd /Users/astra/nfl-props-bml
  . .venv/bin/activate
  export SNITCH_SECRET="<long-real-secret, never commit>"
  python ios/backend/snapshot_server.py --stats cache/player_stats.csv \
      --out ios/PropDesk/PropDesk/Assets.xcassets/props_snapshot.json
(For dev preview the app tolerates an unsigned snapshot; for a real build
wire SnapshotClient.verify with the injected secret.)

## Build to a device / simulator
- Open PropDesk.xcodeproj, select a real device (or simulator) as destination.
- Product > Run. First real-device run: Xcode prompts to register the device
  and manages development signing automatically.

## Archive + upload to TestFlight
1. Choose Product > Archive (device-class destination).
2. In the Organizer > Archives, select the new archive > Distribute App.
3. Choose "TestFlight & App Store" (the default) OR "TestFlight Internal
   Only" for a test build that cannot go to review later.
4. With automatic signing selected + your team, Xcode signs, uploads to App
   Store Connect, and shows a link to the builds page.

## Manage testers (App Store Connect)
- Internal group: create group, add the build, add App Store Connect users
  (up to 100). No review, near-instant.
- External group: invite by email or public link (no ASC account needed,
  up to 10K, but the build goes through Beta App Review first).
- Testers install the free TestFlight app, redeem the invite, install, test,
  and give feedback.

## Each iteration
- Bump CURRENT_PROJECT_VERSION (build number) in project.yml before re-archiving.
- Repeat archive > distribute; newest build of the same version wins.

## Do NOT do
- Commit the SNITCH_SECRET, signing keys (.p8/.p12/pfx), provisioning profiles,
  or .env. They live in Keychain / CI secrets / env vars.
- Upload an "Internal Only" build and later try to submit that same build to
  App Review — use the standard App Store Connect path for the final build.
- Ship a client that embeds the odds API key; the signed-snapshot architecture
  keeps it server-side (standing secrets rule).

Authoritative docs (re-verify; Apple moves them):
- developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases
- help.apple.com/xcode/mac/current/dev2539d985f.html (TestFlight, iOS)
- developer.apple.com/tutorials/develop-in-swift/test-your-beta-app
- TN3125 Inside Code Signing/Provisioning Profiles