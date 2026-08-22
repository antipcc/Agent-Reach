import SwiftUI

/// The round, weightless control the app uses everywhere: header icons,
/// page chevrons, share and delete.
struct GlassCircleButton: View {
    let systemImage: String
    var size: CGFloat = Theme.Metric.controlSize
    var tint: Color = Theme.Palette.ink
    var background: Color = Theme.Palette.surface
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: size * 0.4, weight: .regular))
                .foregroundStyle(tint)
                .frame(width: size, height: size)
                .background(Circle().fill(background))
                .wooLift(radius: 8, y: 2, opacity: 0.06)
        }
        .buttonStyle(.plain)
        .contentShape(Circle())
    }
}

/// A dark capsule with an optional leading glyph — "Create 360°", "Minimize".
struct PillButton: View {
    let title: String
    var systemImage: String?
    var filled: Bool = true
    var tint: Color = Theme.Palette.ink
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                if let systemImage {
                    Image(systemName: systemImage)
                        .font(.system(size: 12, weight: .medium))
                }
                Text(title)
                    .font(Theme.Font.button)
            }
            .foregroundStyle(filled ? Color.white : tint)
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(
                Capsule().fill(filled ? tint : Theme.Palette.surface)
            )
            .wooLift(radius: 10, y: 3, opacity: filled ? 0.16 : 0.06)
        }
        .buttonStyle(.plain)
    }
}
