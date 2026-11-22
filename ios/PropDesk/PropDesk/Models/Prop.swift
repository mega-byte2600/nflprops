import Foundation

/// A single priced prop from the engine snapshot (server-side, keyless).
/// Mirrors the Python snapshot schema (snapshot_server.py) field-for-field.
struct Prop: Codable, Identifiable {
    let player: String
    let stat: String
    let line: Double
    let pOver: Double
    let mean: Double
    let median: Double
    let ciLow: Double
    let ciHigh: Double
    let ciLevel: Double
    let fairPriceHonestNote: String
    let edge: Double?
    let kellyStake: Double?

    var id: String { "\(player)-\(stat)-\(line)" }

    enum CodingKeys: String, CodingKey {
        case player, stat, line
        case pOver = "p_over"
        case mean, median
        case ciLow = "ci_low"
        case ciHigh = "ci_high"
        case ciLevel = "ci_level"
        case fairPriceHonestNote = "fair_price_honest_note"
        case edge
        case kellyStake = "kelly_stake"
    }

    /// Honest over-probability as a display percentage.
    var pOverPercent: String { String(format: "%.1f%%", pOver * 100) }

    /// Human label for the stat ticker, e.g. "rec Yds" / "rush Yds".
    var statLabel: String {
        switch stat {
        case "receiving_yards": return "rec Yds"
        case "rushing_yards": return "rush Yds"
        case "passing_yards": return "pass Yds"
        case "receptions": return "rec"
        case "passing_tds": return "pass TD"
        case "rushing_tds": return "rush TD"
        case "receiving_tds": return "rec TD"
        default: return stat
        }
    }
}