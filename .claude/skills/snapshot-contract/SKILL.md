---
name: snapshot-contract
description: Owns the data contract between the Python snapshot builder (ios/backend) and the Swift app (ios/PropDesk) - schema, versioning, Ed25519 signing, golden fixtures shared by pytest and XCTest. Use whenever a field, type, signing step or file format crosses the Python/Swift boundary.
---

# snapshot-contract: one fixture, two languages, no drift

Governing decisions: ADR-0001 (thin client), ADR-0002 (Ed25519 over exact bytes), ADR-0004
(line provenance).

## The contract
- **Envelope:** `{"key_id": str, "payload_b64": str, "sig_b64": str}`. The signature covers
  the exact payload bytes; nothing is re-serialised to verify.
- **Payload:** `schema_version` ("MAJOR.MINOR"), `generated_utc`, `data_as_of`,
  `audit_as_of`, `stats` (per stat: `gate` PASS/FAIL, gap, `brier_skill`), and `props[]`.
- **Each prop:** `player`, `stat`, `line`, `line_source`, `line_as_of`, `p_over` (null when
  the stat fails the gate), `median`, `q10`, `q90`, `edge` (null unless `line_source` is a
  real market), `experimental` (bool).
- **Versioning:** adding a field bumps MINOR; renaming, removing or changing a type bumps
  MAJOR. The app rejects an unknown MAJOR with a clear "update the app" message.

## Steps for any boundary change
1. Write the change as a schema diff in the PR description.
2. Regenerate `tests/fixtures/snapshot_golden.json` (and the signed envelope) from fixed
   fixture data with a fixed seed and a test-only key. **Never use the production key.**
3. pytest: the builder output equals the golden file; sign and verify pass; a one-byte tamper
   fails; `edge` is not null only with a real `line_source`.
4. XCTest: decode the same golden file (added to the test bundle); verify the signature with
   the test public key; the tampered fixture fails; an unknown `key_id` fails; an unknown
   MAJOR fails.
5. `/review`, then a PR. Both CI jobs (Linux pytest and macOS xcodebuild) must be green.

## Never
Embed a private key or shared secret in the app. Ship an "unsigned is fine in dev" path in
release code. Let Swift re-encode JSON to check a signature.
