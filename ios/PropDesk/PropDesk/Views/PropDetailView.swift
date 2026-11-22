import SwiftUI

/// Detail: the honest engine view — distribution, variance, fair-price caveat,
/// and a clear note that single-game edge is within noise.
struct PropDetailView: View {
    let prop: Prop
    @State private var showCrossChecks = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                header

                Divider()

                // Distribution bar: median + CI band relative to the line.
                distributionBar

                metrics
                honestyPanel

                // Cross-check toggle (Madden / team-EPA prior are priors, never
                // the anchor — the closing line stays the calibration anchor).
                crossCheck
            }
            .padding()
        }
        .navigationTitle(prop.statLabel)
        .navigationBarTitleDisplayMode(.inline)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(prop.player).font(.title2).bold()
            Text("\(prop.statLabel) O/U \(String(format: "%.1f", prop.line))")
                .font(.subheadline).foregroundColor(.secondary)
        }
    }

    private var distributionBar: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Model distribution", systemImage: "chart.bar.xaxis")
                .font(.headline)
            GeometryReader { geo in
                let w = geo.size.width
                let lo = CGFloat(prop.ciLow), hi = CGFloat(prop.ciHigh)
                let span = max(hi - lo, 1)
                let lineX = CGFloat(prop.line)
                let rel = (lineX - lo) / span
                ZStack(alignment: .bottomLeading) {
                    // CI band
                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color.blue.opacity(0.25))
                        .frame(width: w)
                    // line marker
                    Rectangle()
                        .fill(Color.orange)
                        .frame(width: 2)
                        .offset(x: max(0, min(w * rel, w - 2)))
                }
            }
            .frame(height: 24)
            HStack {
                Text("\(prop.ciLow, specifier: "%.0f")") // lo
                Spacer()
                Text("median \(prop.median, specifier: "%.0f")")
                Spacer()
                Text("\(prop.ciHigh, specifier: "%.0f")") // hi
            }
            .font(.caption).foregroundColor(.secondary)
        }
    }

    private var metrics: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("Decision metrics", systemImage: "equal.circle")
                .font(.headline)
            metricRow("Model P(over)", prop.pOverPercent)
            metricRow("Mean", String(format: "%.1f", prop.mean))
            metricRow("Median (what books often price)", String(format: "%.1f", prop.median))
            if let edge = prop.edge {
                metricRow("Edge vs fair", String(format: "%+.1f%%", edge * 100))
            } else {
                metricRow("Edge vs fair", "—")
            }
        }
    }

    private func metricRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label).font(.subheadline).foregroundColor(.secondary)
            Spacer()
            Text(value).font(.subheadline).bold()
        }
    }

    private var honestyPanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Honest limits", systemImage: "exclamationmark.shield")
                .font(.headline)
            Text("Raw per-player fits are NOT calibrated (PIT shows this). This is a distribution estimate, not a guaranteed edge. Single-game edge is within noise — judge only over many bets via CLV/calibration.")
                .font(.footnote)
                .foregroundColor(.orange)
            Text(prop.fairPriceHonestNote)
                .font(.caption2).foregroundColor(.secondary)
        }
        .padding()
        .background(Color.orange.opacity(0.08))
        .cornerRadius(10)
    }

    private var crossCheck: some View {
        VStack(alignment: .leading, spacing: 6) {
            Button {
                withAnimation { showCrossChecks.toggle() }
            } label: {
                HStack {
                    Text("Cross-checks (Madden / team-EPA prior)")
                        .font(.subheadline).foregroundColor(.accentColor)
                    Spacer()
                    Image(systemName: showCrossChecks ? "chevron.up" : "chevron.down")
                }
            }
            if showCrossChecks {
                Text("Cross-check priors refine the player history; the CLOSING LINE is the calibration anchor. A prior alone is weaker than the market (measured: Madden 61.0% SU vs 66.2% closing).")
                    .font(.footnote).foregroundColor(.secondary)
            }
        }
    }
}