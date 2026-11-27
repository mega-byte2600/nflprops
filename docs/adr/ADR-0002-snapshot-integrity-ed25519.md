# ADR-0002: Snapshot integrity with Ed25519 public-key signatures over exact bytes

Status: Proposed (2026-11-27). Supersedes the HMAC-SHA256 design in `snapshot_server.py` and
`SnapshotClient.swift`.

## Context
The scaffold signs with HMAC-SHA256 and a shared secret that "the server and app both hold".
That has two defects:
1. **A secret in an app is not a secret.** Anyone can extract it from the IPA. Whoever holds it
   can sign a forged snapshot that the app accepts, so HMAC with an embedded key gives no
   integrity against an attacker. The scaffold's own comment concedes this.
2. **Canonicalisation mismatch.** Python signs `json.dumps(payload, sort_keys=True)`; Swift
   re-encodes the decoded payload with `JSONEncoder(.sortedKeys)` and recomputes. The two
   serialisers differ in float formatting, `/` escaping and whitespace, so valid snapshots
   would fail to verify. Re-serialising decoded data is not a sound way to verify a signature.

## Decision
1. Sign with **Ed25519** (RFC 8032). The private key lives only in the server's secret store,
   and the app embeds only the **public** key. On iOS use `CryptoKit` `Curve25519.Signing`;
   on Python use the `cryptography` package.
2. Sign the **exact bytes**: the envelope is `{"payload_b64": <base64 of payload JSON bytes>,
   "sig_b64": <signature over those bytes>, "key_id": "..."}`. The app verifies the signature
   over the decoded base64 bytes and only then JSON-decodes them. Nothing is re-serialised.
3. Use a `key_id` so a key can be rotated: the app ships the current and the next public key.
4. If verification fails, the snapshot is rejected and the last verified snapshot is shown,
   labelled with its as-of date.

## Consequences
- No secret ships in the app. A leaked public key is harmless.
- The bundled preview snapshot is signed too, so development builds exercise the real path.
  There is no "unsigned is OK in dev" branch in shipping code.

## Verification
- pytest: sign, verify and tamper (flip one byte, so verification must fail).
- XCTest: verify the golden signed fixture; a tampered fixture must fail; an unknown `key_id` must fail.
