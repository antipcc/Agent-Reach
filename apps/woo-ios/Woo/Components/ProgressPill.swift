import SwiftUI

/// The status capsule used while a model is working — "Creating your 360°
/// look 42%", "Refining your new look".
struct ProgressPill: View {
    let title: String
    /// `nil` for indeterminate work, where a percentage would be a lie.
    var progress: Double?
    var onLight: Bool = false

    private var foreground: Color { onLight ? Theme.Palette.ink : .white }

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: "sparkles")
                .font(.system(size: 12, weight: .medium))
            Text(title)
                .font(Theme.Font.hint)
            if let progress {
                Spacer(minLength: 12)
                Text("\(Int((progress * 100).rounded()))%")
                    .font(Theme.Font.hint.monospacedDigit())
            }
        }
        .foregroundStyle(foreground)
        .padding(.horizontal, 16)
        .padding(.vertical, 11)
        .background(
            Capsule().fill(onLight ? Theme.Palette.surface : Color.black.opacity(0.55))
        )
        .wooLift(radius: 10, y: 3, opacity: 0.12)
    }
}

/// Hairline progress track drawn under the pill during generation.
struct ThinProgressBar: View {
    var progress: Double
    var tint: Color = .white

    var body: some View {
        GeometryReader { proxy in
            ZStack(alignment: .leading) {
                Capsule().fill(tint.opacity(0.2))
                Capsule()
                    .fill(tint)
                    .frame(width: max(0, min(1, progress)) * proxy.size.width)
                    .animation(Theme.Motion.gentle, value: progress)
            }
        }
        .frame(height: 3)
        .accessibilityValue("\(Int((progress * 100).rounded())) percent")
    }
}
