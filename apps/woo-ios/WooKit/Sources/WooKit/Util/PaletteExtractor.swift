import Foundation

/// Pulls the dominant colours out of a look — the row of dots under the card.
/// Implemented in the app layer with Core Image; WooKit only knows the seam.
public protocol PaletteExtractor: Sendable {
    /// Up to `count` hex strings (`#RRGGBB`), most prominent first.
    func palette(from image: ImageData, count: Int) -> [String]
}

/// Used when no extractor is supplied: no dots rather than made-up ones.
public struct EmptyPaletteExtractor: PaletteExtractor {
    public init() {}
    public func palette(from image: ImageData, count: Int) -> [String] { [] }
}
