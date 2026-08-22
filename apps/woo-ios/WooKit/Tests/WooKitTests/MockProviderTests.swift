import XCTest
@testable import WooKit

final class MockProviderTests: XCTestCase {
    private let photo = ImageData.jpeg(Data([0xFF, 0xD8, 0xFF, 0xE0, 0x01, 0x02]))

    func testTryOnReportsProgressThatOnlyEverMovesForwardAndEndsAtOne() async throws {
        let recorder = ProgressRecorder()
        let service = MockTryOnService(latency: .instant)

        _ = try await service.tryOn(person: photo, garments: [photo], progress: recorder.handler)

        let values = recorder.recorded
        XCTAssertEqual(values.first, 0)
        XCTAssertEqual(values.last, 1)
        XCTAssertEqual(values, values.sorted(), "Progress must never go backwards")
    }

    func testTryOnRefusesAnEmptySelectionInsteadOfReturningThePersonUnchanged() async {
        let service = MockTryOnService(latency: .instant)
        do {
            _ = try await service.tryOn(person: photo, garments: [], progress: { _ in })
            XCTFail("Expected a failure for an empty selection")
        } catch let error as WooError {
            guard case .aiFailed = error else { return XCTFail("Unexpected error \(error)") }
        } catch {
            XCTFail("Unexpected error \(error)")
        }
    }

    func testGarmentExtractionIsStableForTheSamePhoto() async throws {
        let service = MockGarmentExtractionService(latency: .instant)
        let first = try await service.extractGarments(from: photo)
        let second = try await service.extractGarments(from: photo)

        XCTAssertEqual(first.map(\.name), second.map(\.name), "A photo must not rename its pieces between runs")
        XCTAssertEqual(first.map(\.category), [.tops, .bottoms, .shoes])
    }

    func testSpinNeedsMoreThanOneFrameToBeATurnaround() async {
        let service = MockSpinService(latency: .instant)
        do {
            _ = try await service.generateSpin(from: photo, frameCount: 1, progress: { _ in })
            XCTFail("Expected a failure for a single frame")
        } catch let error as WooError {
            guard case .aiFailed = error else { return XCTFail("Unexpected error \(error)") }
        } catch {
            XCTFail("Unexpected error \(error)")
        }
    }

    func testSpinProducesExactlyTheFramesItWasAskedFor() async throws {
        let service = MockSpinService(latency: .instant)
        let result = try await service.generateSpin(from: photo, frameCount: 12, progress: { _ in })
        XCTAssertEqual(result.frames.count, 12)
    }

    func testAnUnconfiguredLiveProviderQuietlyStaysOnTheMocks() {
        let provider = AIProvider.live(config: .empty)
        XCTAssertTrue(provider.tryOn is MockTryOnService)
        XCTAssertTrue(provider.spin is MockSpinService)
    }

    func testALiveConfigOnlyTakesOverTheEndpointsItActuallyDefines() throws {
        let config = AIConfig(
            baseURL: URL(string: "https://example.invalid"),
            apiKey: "k",
            tryOnPath: "/try-on"
        )
        let provider = AIProvider.live(config: config)
        XCTAssertTrue(provider.tryOn is HTTPAIService, "Try-on was configured, so it must go over the wire")
        XCTAssertTrue(provider.spin is MockSpinService, "360° was not configured, so it must stay mocked")
    }

    func testAConfigWithoutAKeyIsNotConsideredConfigured() {
        let config = AIConfig(baseURL: URL(string: "https://example.invalid"), tryOnPath: "/try-on")
        XCTAssertFalse(config.isConfigured)
    }
}
