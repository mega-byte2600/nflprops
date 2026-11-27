import XCTest
@testable import PropDesk

/// The bundled snapshot decodes against the Swift model and is self-consistent.
/// (Signature verification moves to Ed25519 in I3; until then an unsigned envelope must
/// never verify.)
final class SnapshotDecodingTests: XCTestCase {
    private func loadFixture() throws -> SnapshotEnvelope {
        let bundle = Bundle(for: SnapshotDecodingTests.self)
        let url = try XCTUnwrap(bundle.url(forResource: "props_snapshot", withExtension: "json"),
                                "props_snapshot.json missing from the test bundle")
        return try JSONDecoder().decode(SnapshotEnvelope.self, from: Data(contentsOf: url))
    }

    func testBundledSnapshotDecodes() throws {
        let env = try loadFixture()
        XCTAssertEqual(env.payload.schemaVersion, "1.0")
        XCTAssertFalse(env.payload.props.isEmpty)
    }

    func testProbabilitiesAndIntervalsAreCoherent() throws {
        for p in try loadFixture().payload.props {
            XCTAssertTrue((0...1).contains(p.pOver), "\(p.id) p_over out of range")
            XCTAssertLessThanOrEqual(p.ciLow, p.median, p.id)
            XCTAssertLessThanOrEqual(p.median, p.ciHigh, p.id)
        }
    }

    func testUnsignedEnvelopeNeverVerifies() throws {
        let env = try loadFixture()
        XCTAssertNil(env.signature)
        XCTAssertFalse(SnapshotClient.verify(env, secret: "any-secret"))
    }

    func testAppLoadsBundledSnapshotAtLaunch() {
        let store = SnapshotStore()
        XCTAssertNil(store.loadError, store.loadError ?? "")
        XCTAssertFalse(store.props.isEmpty)
    }
}
