import Foundation

/// Top-level signed snapshot envelope received from the backend.
/// `signature` is HMAC-SHA256 hex over the canonical JSON of `payload`; the
/// app verifies it against its bundled shared secret (never embedded as a
/// real secret in production - login token / config-injected in real use).
struct SnapshotEnvelope: Codable {
    let signature: String?
    let payload: SnapshotPayload
}

struct SnapshotPayload: Codable {
    let schemaVersion: String
    let generatedUtc: String
    let engine: EngineInfo
    let honesty: String
    let props: [Prop]

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case generatedUtc = "generated_utc"
        case engine, honesty, props
    }
}

struct EngineInfo: Codable {
    let ciDefault: Double
    let nMonteCarlo: Int

    enum CodingKeys: String, CodingKey {
        case ciDefault = "ci_default"
        case nMonteCarlo = "n_monte_carlo"
    }
}