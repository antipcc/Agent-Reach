import Foundation

/// Drives the oversized watermark behind the outfit on the home card.
public enum Season: String, Codable, CaseIterable, Sendable {
    case spring, summer, fall, winter

    /// `SPRING`, `SUMMER`, `FALL`, `WINTER` — rendered as-is on the card.
    public var watermark: String { rawValue.uppercased() }
}
