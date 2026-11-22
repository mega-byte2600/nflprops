import SwiftUI

/// Settings / about screen: honest framing and backend wiring notes.
struct SettingsView: View {
    @EnvironmentObject var store: SnapshotStore

    var body: some View {
        List {
            Section("About") {
                LabeledContent("Product", value: "Prop Desk (NFL)")
                LabeledContent("Version", value: "0.1.0")
                if let gen = store.generatedUtc {
                    LabeledContent("Snapshot", value: gen)
                }
            }
            Section("Honest framing") {
                Text(store.honestyNote ?? "Distributions + CI only; judged by CLV/calibration over many bets, not short-run ROI.")
                    .font(.footnote)
            }
            Section("Backend") {
                LabeledContent("Architecture", value: "signed snapshot, no client key")
                Text("Run: venv/bin/python ios/backend/snapshot_server.py --stats cache/player_stats.csv --out PropDesk/Assets.xcassets/props_snapshot.json\n\nThe app reads the server-precomputed signed snapshot; the odds API key stays server-side.")
                    .font(.caption).foregroundColor(.secondary)
            }
        }
        .navigationTitle("Settings")
    }
}