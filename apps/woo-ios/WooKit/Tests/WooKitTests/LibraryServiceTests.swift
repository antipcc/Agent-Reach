import XCTest
@testable import WooKit

final class LibraryServiceTests: XCTestCase {
    private let photo = ImageData.jpeg(Data([0xFF, 0xD8, 0xFF, 0xE0, 0x11, 0x22]))

    private func makeService() -> LibraryService {
        LibraryService(
            store: InMemoryOutfitStore(),
            provider: .mock(latency: .none),
            palette: StubPalette()
        )
    }

    func testIngestingAPhotoStoresACutoutTheOriginalAndAPalette() async throws {
        let service = makeService()
        let outfit = try await service.ingestPhoto(photo, source: .camera)

        XCTAssertEqual(outfit.source, .camera)
        XCTAssertNotNil(outfit.original, "The original must be kept so pieces can be re-extracted later")
        XCTAssertEqual(outfit.palette, ["#112233"])

        let snapshot = try await service.snapshot()
        XCTAssertEqual(snapshot.outfits.map(\.id), [outfit.id])
        let cutout = try await service.store.readAsset(outfit.cutout)
        XCTAssertFalse(cutout.isEmpty)
    }

    func testExtractingGarmentsFillsTheWardrobeAndLinksBackToTheLook() async throws {
        let service = makeService()
        let outfit = try await service.ingestPhoto(photo)

        let items = try await service.extractGarments(for: outfit.id)

        XCTAssertEqual(items.count, 3)
        XCTAssertEqual(items.compactMap(\.sourceOutfitID), Array(repeating: outfit.id, count: 3))

        let snapshot = try await service.snapshot()
        XCTAssertEqual(Set(snapshot.outfits[0].itemIDs), Set(items.map(\.id)))
        XCTAssertEqual(snapshot.itemsByCategory().map(\.category), [.tops, .bottoms, .shoes])
    }

    func testReExtractingReplacesThePreviousPiecesInsteadOfDuplicatingThem() async throws {
        let service = makeService()
        let outfit = try await service.ingestPhoto(photo)
        _ = try await service.extractGarments(for: outfit.id)
        let second = try await service.extractGarments(for: outfit.id)

        let snapshot = try await service.snapshot()
        XCTAssertEqual(snapshot.items.count, 3, "A second pass must not leave the first pass behind")
        XCTAssertEqual(Set(snapshot.outfits[0].itemIDs), Set(second.map(\.id)))
    }

    func testGeneratingASpinAttachesTheFramesAndReportsProgress() async throws {
        let service = makeService()
        let outfit = try await service.ingestPhoto(photo)

        let recorder = ProgressRecorder()
        let updated = try await service.generateSpin(
            for: outfit.id,
            frameCount: 8,
            progress: recorder.handler
        )

        XCTAssertTrue(updated.hasSpin)
        XCTAssertEqual(updated.spin?.frameCount, 8)
        XCTAssertEqual(recorder.recorded.last, 1)
        XCTAssertEqual(recorder.recorded, recorder.recorded.sorted())
    }

    func testRegeneratingASpinDropsTheFramesItReplaced() async throws {
        let service = makeService()
        let outfit = try await service.ingestPhoto(photo)
        let first = try await service.generateSpin(for: outfit.id, frameCount: 4)
        let staleFrame = try XCTUnwrap(first.spin?.frames.first)

        _ = try await service.generateSpin(for: outfit.id, frameCount: 4)

        do {
            _ = try await service.store.readAsset(staleFrame)
            XCTFail("The superseded frames should have been cleaned up")
        } catch let error as WooError {
            XCTAssertEqual(error, .assetNotFound(staleFrame.filename))
        }
    }

    func testWorkingOnAMissingOutfitSaysSoRatherThanFailingSilently() async {
        let service = makeService()
        let ghost = UUID()
        do {
            _ = try await service.extractGarments(for: ghost)
            XCTFail("Expected a missing-outfit error")
        } catch let error as WooError {
            XCTAssertEqual(error, .outfitNotFound(ghost))
        } catch {
            XCTFail("Unexpected error \(error)")
        }
    }

    func testTryingOnSavedPiecesProducesAnImageThatCanBecomeItsOwnLook() async throws {
        let service = makeService()
        let outfit = try await service.ingestPhoto(photo)
        let items = try await service.extractGarments(for: outfit.id)

        let rendering = try await service.tryOn(person: photo, itemIDs: items.map(\.id))
        XCTAssertFalse(rendering.isEmpty)

        let saved = try await service.saveTryOnResult(rendering, itemIDs: items.map(\.id), isFavorite: true)
        XCTAssertEqual(saved.source, .tryOn)
        XCTAssertTrue(saved.isFavorite)

        let snapshot = try await service.snapshot()
        XCTAssertEqual(snapshot.outfits.count, 2, "The try-on result is a look of its own")
    }

    func testTryingOnNothingIsRefused() async throws {
        let service = makeService()
        do {
            _ = try await service.tryOn(person: photo, itemIDs: [])
            XCTFail("Expected a failure for an empty selection")
        } catch let error as WooError {
            guard case .aiFailed = error else { return XCTFail("Unexpected error \(error)") }
        }
    }

    func testFavouritingPersists() async throws {
        let service = makeService()
        let outfit = try await service.ingestPhoto(photo)
        _ = try await service.setFavorite(true, outfitID: outfit.id)

        let snapshot = try await service.snapshot()
        XCTAssertEqual(snapshot.outfits.first?.isFavorite, true)
    }
}

/// Fixed palette so assertions do not depend on real colour sampling.
private struct StubPalette: PaletteExtractor {
    func palette(from image: ImageData, count: Int) -> [String] {
        Array(repeating: "#112233", count: min(count, 1))
    }
}
