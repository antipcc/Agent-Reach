import XCTest
@testable import WooKit

final class ModelTests: XCTestCase {
    func testOutfitSurvivesACodingRoundTrip() throws {
        let outfit = Outfit(
            date: Date(timeIntervalSince1970: 1_787_000_000),
            cutout: AssetRef(filename: "cutout-a.png"),
            original: AssetRef(filename: "original-a.jpeg"),
            palette: ["#F2E6D8", "#1B1B1B"],
            season: .fall,
            itemIDs: [UUID()],
            spin: SpinAsset(frames: [AssetRef(filename: "spin-0.png"), AssetRef(filename: "spin-1.png")]),
            isFavorite: true,
            source: .tryOn
        )

        let data = try LibraryCoding.encoder.encode(outfit)
        let decoded = try LibraryCoding.decoder.decode(Outfit.self, from: data)
        XCTAssertEqual(decoded, outfit)
    }

    func testSeasonFollowsTheDateUntilItIsPinned() {
        var outfit = Outfit(
            date: DateComponents(calendar: .current, year: 2026, month: 8, day: 21).date!,
            cutout: AssetRef(filename: "c.png")
        )
        XCTAssertEqual(outfit.resolvedSeason(), .summer)

        outfit.season = .winter
        XCTAssertEqual(outfit.resolvedSeason(), .winter, "A pinned season must win over the date")
    }

    func testOwnedAssetsCoverEverythingTheOutfitAloneCanDelete() {
        let outfit = Outfit(
            cutout: AssetRef(filename: "cutout.png"),
            original: AssetRef(filename: "original.png"),
            spin: SpinAsset(frames: [AssetRef(filename: "s0.png"), AssetRef(filename: "s1.png")])
        )
        XCTAssertEqual(
            Set(outfit.ownedAssets.map(\.filename)),
            ["cutout.png", "original.png", "s0.png", "s1.png"]
        )
    }

    func testSpinFramesWrapInBothDirections() {
        let spin = SpinAsset(frames: (0..<4).map { AssetRef(filename: "s\($0).png") })
        XCTAssertEqual(spin.frame(at: 0)?.filename, "s0.png")
        XCTAssertEqual(spin.frame(at: 5)?.filename, "s1.png")
        XCTAssertEqual(spin.frame(at: -1)?.filename, "s3.png", "Dragging backwards past zero must keep spinning")
        XCTAssertNil(SpinAsset(frames: []).frame(at: 0))
    }

    func testAssetRefInfersItsFormatFromTheExtension() {
        XCTAssertEqual(AssetRef(filename: "a.png").inferredFormat, .png)
        XCTAssertEqual(AssetRef(filename: "a.jpeg").inferredFormat, .jpeg)
        XCTAssertEqual(AssetRef(filename: "a.jpg").inferredFormat, .jpeg)
        XCTAssertEqual(AssetRef(filename: "noextension").inferredFormat, .png)
    }

    func testSeasonBucketsCoverEveryMonth() {
        let expected: [Int: Season] = [
            1: .winter, 2: .winter, 3: .spring, 4: .spring, 5: .spring,
            6: .summer, 7: .summer, 8: .summer, 9: .fall, 10: .fall,
            11: .fall, 12: .winter
        ]
        for (month, season) in expected {
            XCTAssertEqual(SeasonResolver.season(forMonth: month), season, "month \(month)")
        }
    }

    func testWardrobeGroupsIntoSectionsInDisplayOrderAndSkipsEmptyOnes() {
        let snapshot = LibrarySnapshot(
            outfits: [],
            items: [
                GarmentItem(name: "Boots", category: .shoes, cutout: AssetRef(filename: "1.png")),
                GarmentItem(name: "Tee", category: .tops, cutout: AssetRef(filename: "2.png")),
                GarmentItem(name: "Skirt", category: .bottoms, cutout: AssetRef(filename: "3.png"))
            ]
        )
        XCTAssertEqual(snapshot.itemsByCategory().map(\.category), [.tops, .bottoms, .shoes])
    }

    func testOutfitsPageNewestFirst() {
        let old = Outfit(date: Date(timeIntervalSince1970: 1000), cutout: AssetRef(filename: "a.png"))
        let recent = Outfit(date: Date(timeIntervalSince1970: 2000), cutout: AssetRef(filename: "b.png"))
        let snapshot = LibrarySnapshot(outfits: [old, recent])
        XCTAssertEqual(snapshot.outfitsNewestFirst.map(\.id), [recent.id, old.id])
    }
}
