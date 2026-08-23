import Foundation

/// Wardrobe sections. Declaration order is display order.
public enum GarmentCategory: String, Codable, CaseIterable, Sendable, Identifiable {
    case tops, outerwear, bottoms, dresses, shoes, bags, accessories

    public var id: String { rawValue }

    /// Section header text on the wardrobe screen.
    public var displayName: String {
        switch self {
        case .tops: return "上装"
        case .outerwear: return "外套"
        case .bottoms: return "下装"
        case .dresses: return "连衣裙"
        case .shoes: return "鞋履"
        case .bags: return "包袋"
        case .accessories: return "配饰"
        }
    }

    /// Position of this section in the wardrobe list.
    public var sortIndex: Int {
        GarmentCategory.allCases.firstIndex(of: self) ?? 0
    }
}
