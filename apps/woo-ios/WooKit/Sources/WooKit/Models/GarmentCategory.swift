import Foundation

/// Wardrobe sections. Declaration order is display order.
public enum GarmentCategory: String, Codable, CaseIterable, Sendable, Identifiable {
    case tops, outerwear, bottoms, dresses, shoes, bags, accessories

    public var id: String { rawValue }

    /// Section header text, e.g. `OUTERWEAR`.
    public var displayName: String { rawValue.uppercased() }

    /// Position of this section in the wardrobe list.
    public var sortIndex: Int {
        GarmentCategory.allCases.firstIndex(of: self) ?? 0
    }
}
