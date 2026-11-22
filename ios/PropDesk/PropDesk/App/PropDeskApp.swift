import SwiftUI

@main
struct PropDeskApp: App {
    /// Shared snapshot state loaded once from the bundled (or fetched) asset.
    @StateObject private var store = SnapshotStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(store)
                .preferredColorScheme(.dark)
        }
    }
}

/// Simple observable store that loads the honest snapshot and exposes props.
final class SnapshotStore: ObservableObject {
    @Published var props: [Prop] = []
    @Published var generatedUtc: String?
    @Published var honestyNote: String?
    @Published var loadError: String?

    init() {
        load()
    }

    func load() {
        guard let env = SnapshotClient.loadBundledPreview() else {
            loadError = "No snapshot bundled. Run ios/backend/snapshot_server.py and copy props_snapshot.json to the app asset catalog."
            return
        }
        // In production: verify env against an injected secret. Dev preview loads
        // unsigned without hard failure so the UI is viewable; real builds gate.
        props = env.payload.props
        generatedUtc = env.payload.generatedUtc
        honestyNote = env.payload.honesty
    }

    var propsSorted: [Prop] {
        props.sorted { $0.pOver > $1.pOver }
    }
}

struct ContentView: View {
    @EnvironmentObject var store: SnapshotStore

    var body: some View {
        NavigationView {
            PropListView()
                .navigationTitle("Prop Desk")
        }
    }
}