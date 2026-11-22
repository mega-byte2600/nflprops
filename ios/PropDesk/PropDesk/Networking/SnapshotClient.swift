import Foundation
import CryptoKit

/// Fetches and verifies the signed prop snapshot from the backend.
///
/// The iPhone app holds NO odds API key and does no heavy compute - it reads a
/// server-precomputed, HMAC-signed snapshot (dkori-protect architecture).
/// In the current dev scaffold the snapshot is bundled as an asset for offline
/// preview; a live build swaps the fetch for the signed file's URL and verifies
/// HMAC with a secret injected at build/setup time (never a checked-in key).
enum SnapshotClient {
    /// Verify the envelope's HMAC-SHA256 signature over the canonical payload
    /// JSON, using the shared secret. Returns false if unsigned or mismatched.
    static func verify(_ envelope: SnapshotEnvelope, secret: String) -> Bool {
        guard let signature = envelope.signature, !secret.isEmpty else { return false }
        let canonical = try? canonicalJSON(from: envelope.payload)
        guard let canonical else { return false }
        let key = SymmetricKey(data: Data(secret.utf8))
        let mac = HMAC<SHA256>.authenticationCode(for: Data(canonical), using: key)
        let expected = mac.map { String(format: "%02x", $0) }.joined()
        return expected == signature.lowercased()
    }

    /// Load the bundled preview snapshot (bundled asset "props_snapshot").
    static func loadBundledPreview() -> SnapshotEnvelope? {
        guard let url = Bundle.main.url(forResource: "props_snapshot",
                                        withExtension: "json"),
              let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(SnapshotEnvelope.self, from: data)
    }

    /// Canonical JSON of the payload (sorted keys) to reproduce what the server
    /// signed. Production would share the exact canonical serializer both sides.
    private static func canonicalJSON<T: Encodable>(from value: T) -> Data? {
        let enc = JSONEncoder()
        enc.outputFormatting = [.sortedKeys]
        return try? enc.encode(value)
    }
}