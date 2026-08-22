import Foundation

/// The whole persisted library in one value: what `library.json` holds.
public struct LibrarySnapshot: Codable, Sendable {
    /// Bumped when the on-disk shape changes so old files can be migrated
    /// instead of silently failing to decode.
    public static let currentVersion = 1

    public var version: Int
    public var outfits: [Outfit]
    public var items: [GarmentItem]

    public init(
        version: Int = LibrarySnapshot.currentVersion,
        outfits: [Outfit] = [],
        items: [GarmentItem] = []
    ) {
        self.version = version
        self.outfits = outfits
        self.items = items
    }

    public static let empty = LibrarySnapshot()

    /// Newest first — the order the home card pages through.
    public var outfitsNewestFirst: [Outfit] {
        outfits.sorted { $0.date > $1.date }
    }

    /// Wardrobe grouped into its sections, empty sections dropped.
    public func itemsByCategory() -> [WardrobeSection] {
        GarmentCategory.allCases.compactMap { category in
            let matching = items
                .filter { $0.category == category }
                .sorted { $0.createdAt > $1.createdAt }
            return matching.isEmpty ? nil : WardrobeSection(category: category, items: matching)
        }
    }
}

/// One headed run of the wardrobe list, e.g. everything under `BOTTOMS`.
public struct WardrobeSection: Identifiable, Hashable, Sendable {
    public let category: GarmentCategory
    public let items: [GarmentItem]

    public var id: GarmentCategory { category }

    public init(category: GarmentCategory, items: [GarmentItem]) {
        self.category = category
        self.items = items
    }
}
