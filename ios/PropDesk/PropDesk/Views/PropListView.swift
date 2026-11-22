import SwiftUI

/// Home: ranked prop list with the honest decision view.
/// Each row shows fair probability (model distribution), the line, the
/// variance band, and a clear honest note. No guaranteed-winner framing.
struct PropListView: View {
    @EnvironmentObject var store: SnapshotStore

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            if let err = store.loadError {
                HStack {
                    Text(err).font(.footnote).foregroundColor(.secondary).lineLimit(3)
                    Spacer()
                }
                .padding()
            } else {
                List(store.propsSorted) { prop in
                    NavigationLink(destination: PropDetailView(prop: prop)) {
                        PropRow(prop: prop)
                    }
                }
                .listStyle(.plain)
            }
        }
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                NavigationLink(destination: SettingsView()) {
                    Image(systemName: "gearshape")
                }
            }
        }
    }
}

struct PropRow: View {
    let prop: Prop

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(prop.player).font(.headline)
                Spacer()
                Text("Over \(String(format: "%.1f", prop.line))")
                    .font(.subheadline).foregroundColor(.secondary)
            }
            HStack(spacing: 12) {
                VStack(alignment: .leading) {
                    Text("Model P(over)").font(.caption2).foregroundColor(.secondary)
                    Text(prop.pOverPercent).font(.title3).bold()
                }
                Divider()
                VStack(alignment: .leading) {
                    Text("Median").font(.caption2).foregroundColor(.secondary)
                    Text(String(format: "%.1f", prop.median)).font(.subheadline)
                }
                Divider()
                VStack(alignment: .leading) {
                    Text("\(String(format: "%.0f%%", prop.ciLevel*100)) CI").font(.caption2).foregroundColor(.secondary)
                    Text("\(String(format: "%.0f", prop.ciLow))–\(String(format: "%.0f", prop.ciHigh))")
                        .font(.subheadline)
                }
                Spacer()
            }
            // honest framing banner
            Text("Distribution estimate, not a market fair price")
                .font(.caption2).foregroundColor(.orange)
        }
        .padding(.vertical, 4)
    }
}