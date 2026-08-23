import Foundation

/// Drives the oversized watermark behind the outfit on the home card.
public enum Season: String, Codable, CaseIterable, Sendable {
    case spring, summer, fall, winter

    /// `SPRING`, `SUMMER`, `FALL`, `WINTER` — rendered as-is on the card.
    /// Deliberately left in English while the rest of the interface is
    /// Chinese: this is set oversized as a graphic, and one or two Chinese
    /// characters carry nothing like the weight of a stretched long word.
    public var watermark: String { rawValue.uppercased() }
}
