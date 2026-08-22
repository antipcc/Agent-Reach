import SwiftUI

/// The colours pulled out of a look, drawn as a short row of dots.
struct PaletteDotsRow: View {
    let hexes: [String]

    var body: some View {
        HStack(spacing: 7) {
            ForEach(Array(hexes.prefix(5).enumerated()), id: \.offset) { _, hex in
                Circle()
                    .fill(Color(hex: hex) ?? Theme.Palette.hairline)
                    .frame(width: Theme.Metric.paletteDot, height: Theme.Metric.paletteDot)
                    .overlay(
                        Circle().strokeBorder(Theme.Palette.hairline, lineWidth: 0.5)
                    )
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(hexes.count) colours in this look")
    }
}

extension Color {
    /// Parses `#RRGGBB` / `RRGGBB`. Returns nil rather than a guess so a bad
    /// value shows as the neutral placeholder instead of a wrong colour.
    init?(hex: String) {
        guard let components = HexColor.components(hex) else { return nil }
        self.init(red: components.red, green: components.green, blue: components.blue)
    }
}
