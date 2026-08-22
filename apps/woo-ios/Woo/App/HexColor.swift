import Foundation

/// Hex strings are how colours travel through the library (`#RRGGBB`).
/// Kept free of SwiftUI so the palette extractor, which works in Core
/// Graphics, does not have to import a UI framework to produce one.
enum HexColor {
    static func string(red: Double, green: Double, blue: Double) -> String {
        let channel = { (value: Double) in Int((min(max(value, 0), 1) * 255).rounded()) }
        return String(format: "#%02X%02X%02X", channel(red), channel(green), channel(blue))
    }

    /// Parses `#RRGGBB` / `RRGGBB` back into components in `0...1`.
    /// Returns nil rather than guessing, so a bad value never becomes a
    /// plausible-looking wrong colour.
    static func components(_ hex: String) -> (red: Double, green: Double, blue: Double)? {
        var value = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        if value.hasPrefix("#") { value.removeFirst() }
        guard value.count == 6, let number = UInt32(value, radix: 16) else { return nil }
        return (
            Double((number & 0xFF0000) >> 16) / 255,
            Double((number & 0x00FF00) >> 8) / 255,
            Double(number & 0x0000FF) / 255
        )
    }
}
