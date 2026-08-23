import XCTest
@testable import WooKit

final class FileOutfitStoreTests: XCTestCase {
    private var root: URL!

    override func setUpWithError() throws {
        root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("woo-tests-\(UUID().uuidString)", isDirectory: true)
    }

    override func tearDownWithError() throws {
        try? FileManager.default.removeItem(at: root)
    }

    func testAnEmptyLibraryLoadsInsteadOfFailing() async throws {
        let store = FileOutfitStore(root: root)
        let snapshot = try await store.load()
        XCTAssertTrue(snapshot.outfits.isEmpty)
        XCTAssertEqual(snapshot.version, LibrarySnapshot.currentVersion)
    }

    func testOutfitsSurviveAFreshStoreInstance() async throws {
        let outfit = Outfit(cutout: AssetRef(filename: "cutout.png"))
        let writer = FileOutfitStore(root: root)
        try await writer.addOutfit(outfit)

        // A second instance reads from disk, not from the first one's cache —
        // this is the "kill the app and reopen it" case.
        let reader = FileOutfitStore(root: root)
        let snapshot = try await reader.load()
        XCTAssertEqual(snapshot.outfits.map(\.id), [outfit.id])
    }

    func testUpdatingAMissingOutfitReportsItRatherThanInsertingIt() async throws {
        let store = FileOutfitStore(root: root)
        let ghost = Outfit(cutout: AssetRef(filename: "gone.png"))
        do {
            try await store.updateOutfit(ghost)
            XCTFail("Expected the update to fail")
        } catch let error as WooError {
            XCTAssertEqual(error, .outfitNotFound(ghost.id))
        }
    }

    func testDeletingAnOutfitTakesItsAssetsButLeavesTheWardrobe() async throws {
        let store = FileOutfitStore(root: root)
        let cutout = AssetRef(filename: "cutout.png")
        let itemRef = AssetRef(filename: "item.png")
        try await store.writeAsset(Data("cutout".utf8), ref: cutout)
        try await store.writeAsset(Data("item".utf8), ref: itemRef)

        let item = GarmentItem(name: "Tee", category: .tops, cutout: itemRef)
        let outfit = Outfit(cutout: cutout, itemIDs: [item.id])
        try await store.addItems([item])
        try await store.addOutfit(outfit)

        try await store.deleteOutfit(id: outfit.id)

        let snapshot = try await store.load()
        XCTAssertTrue(snapshot.outfits.isEmpty)
        XCTAssertEqual(snapshot.items.map(\.id), [item.id], "The wardrobe outlives the look it came from")
        XCTAssertFalse(FileManager.default.fileExists(atPath: store.assetURL(cutout).path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: store.assetURL(itemRef).path))
    }

    func testDeletingAWardrobeItemUnlinksItFromEveryOutfit() async throws {
        let store = FileOutfitStore(root: root)
        let itemRef = AssetRef(filename: "item.png")
        try await store.writeAsset(Data("item".utf8), ref: itemRef)
        let item = GarmentItem(name: "Skirt", category: .bottoms, cutout: itemRef)
        let outfit = Outfit(cutout: AssetRef(filename: "c.png"), itemIDs: [item.id])
        try await store.addItems([item])
        try await store.addOutfit(outfit)

        try await store.deleteItem(id: item.id)

        let snapshot = try await store.load()
        XCTAssertTrue(snapshot.items.isEmpty)
        XCTAssertEqual(snapshot.outfits.first?.itemIDs, [], "A deleted piece must not leave a dangling id")
    }

    func testAssetsRoundTripAndReportWhenMissing() async throws {
        let store = FileOutfitStore(root: root)
        let ref = AssetRef.generated(prefix: "cutout")
        try await store.writeAsset(Data([0x89, 0x50, 0x4E, 0x47]), ref: ref)
        let written = try await store.readAsset(ref)
        XCTAssertEqual(written.count, 4)

        await store.deleteAsset(ref)
        do {
            _ = try await store.readAsset(ref)
            XCTFail("Expected a missing-asset error")
        } catch let error as WooError {
            XCTAssertEqual(error, .assetNotFound(ref.filename))
        }
    }

    func testACorruptLibraryFileSurfacesAsSuchInsteadOfCrashing() async throws {
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try Data("not json".utf8).write(to: root.appendingPathComponent("library.json"))

        let store = FileOutfitStore(root: root)
        do {
            _ = try await store.load()
            XCTFail("Expected a corruption error")
        } catch let error as WooError {
            guard case .libraryCorrupted = error else {
                return XCTFail("Expected .libraryCorrupted, got \(error)")
            }
        }
    }
}
