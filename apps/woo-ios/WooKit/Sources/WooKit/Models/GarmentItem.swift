import Foundation

/// A single piece of clothing lifted out of an outfit photo and filed in the wardrobe.
public struct GarmentItem: Identifiable, Codable, Hashable, Sendable {
    public let id: UUID
    public var name: String
    public var category: GarmentCategory
    public var cutout: AssetRef
    public var colorHex: String?
    /// The outfit this item was extracted from, if any. Kept for provenance —
    /// deleting that outfit does not delete the item, the wardrobe outlives it.
    public var sourceOutfitID: UUID?
    public var createdAt: Date

    public init(
        id: UUID = UUID(),
        name: String,
        category: GarmentCategory,
        cutout: AssetRef,
        colorHex: String? = nil,
        sourceOutfitID: UUID? = nil,
        createdAt: Date = Date()
    ) {
        self.id = id
        self.name = name
        self.category = category
        self.cutout = cutout
        self.colorHex = colorHex
        self.sourceOutfitID = sourceOutfitID
        self.createdAt = createdAt
    }
}
