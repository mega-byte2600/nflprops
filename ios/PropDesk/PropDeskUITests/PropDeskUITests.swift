import XCTest

/// I6 (ADR-0008): screenshots of each screen at the default text size and at the largest
/// accessibility size, kept as CI artifacts for `/ios-ux review`, plus Apple's built-in
/// accessibility audit. The app currently forces dark mode, so only dark is captured.
final class PropDeskUITests: XCTestCase {
    override func setUp() { continueAfterFailure = true }

    private func launch(contentSize: String?) -> XCUIApplication {
        let app = XCUIApplication()
        if let size = contentSize {
            app.launchArguments += ["-UIPreferredContentSizeCategoryName", size]
        }
        app.launch()
        return app
    }

    private func snap(_ app: XCUIApplication, _ name: String) {
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = name
        shot.lifetime = .keepAlways
        add(shot)
    }

    private func tour(_ app: XCUIApplication, label: String) {
        XCTAssertTrue(app.navigationBars["Prop Desk"].waitForExistence(timeout: 10))
        snap(app, "01-list-\(label)")
        let firstRow = app.cells.firstMatch
        XCTAssertTrue(firstRow.waitForExistence(timeout: 5), "no prop rows rendered")
        firstRow.tap()
        snap(app, "02-detail-\(label)")
        app.navigationBars.buttons.firstMatch.tap()
        let gear = app.navigationBars.buttons["gearshape"]
        if gear.waitForExistence(timeout: 3) {
            gear.tap()
            snap(app, "03-settings-\(label)")
        }
    }

    func testScreenshotsDefaultSize() {
        tour(launch(contentSize: nil), label: "default")
    }

    func testScreenshotsLargestAccessibilitySize() {
        tour(launch(contentSize: "UICTContentSizeCategoryAccessibilityXXXL"), label: "AX5")
    }

    /// Runs Apple's audit. Real accessibility issues are reported as test failures by the
    /// audit itself and are never retried. Only the infrastructure error "Audit failed to
    /// complete in time" (code -56, seen on a loaded CI simulator) gets one retry.
    @available(iOS 17.0, *)
    private func audit(_ app: XCUIApplication) throws {
        do {
            try app.performAccessibilityAudit()
        } catch let error as NSError
            where error.domain == "com.apple.xcode.xctest.accessibilityAudit" && error.code == -56 {
            try app.performAccessibilityAudit()
        }
    }

    func testAccessibilityAuditListScreen() throws {
        guard #available(iOS 17.0, *) else { throw XCTSkip("performAccessibilityAudit needs iOS 17") }
        let app = launch(contentSize: nil)
        XCTAssertTrue(app.navigationBars["Prop Desk"].waitForExistence(timeout: 10))
        try audit(app)
    }

    func testAccessibilityAuditDetailScreen() throws {
        guard #available(iOS 17.0, *) else { throw XCTSkip("performAccessibilityAudit needs iOS 17") }
        let app = launch(contentSize: nil)
        XCTAssertTrue(app.cells.firstMatch.waitForExistence(timeout: 10))
        app.cells.firstMatch.tap()
        try audit(app)
    }
}
