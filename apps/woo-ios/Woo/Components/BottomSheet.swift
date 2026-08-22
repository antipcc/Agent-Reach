import SwiftUI

/// A sheet that is always on screen, with two resting heights: collapsed
/// (palette and date) and expanded (the pieces in the look).
///
/// Hand-rolled rather than `.sheet(…)` with detents because it has to coexist
/// with full-screen covers and stay put while the card behind it is dragged.
enum SheetDetent {
    case collapsed, expanded
}

struct BottomSheet<Content: View>: View {
    @Binding var detent: SheetDetent
    let collapsedHeight: CGFloat
    let expandedHeight: CGFloat
    @ViewBuilder var content: () -> Content

    @State private var dragOffset: CGFloat = 0

    private var restingHeight: CGFloat {
        detent == .collapsed ? collapsedHeight : expandedHeight
    }

    /// Clamped so the sheet can be pulled a little past its stops but never
    /// off the screen or over the masthead.
    private var height: CGFloat {
        min(max(restingHeight - dragOffset, collapsedHeight - 24), expandedHeight + 24)
    }

    var body: some View {
        VStack(spacing: 0) {
            Capsule()
                .fill(Theme.Palette.inkTertiary.opacity(0.5))
                .frame(width: Theme.Metric.grabberWidth, height: Theme.Metric.grabberHeight)
                .padding(.top, 10)
                .padding(.bottom, 12)

            content()
                .frame(maxHeight: .infinity, alignment: .top)
        }
        .frame(maxWidth: .infinity)
        .frame(height: height, alignment: .top)
        .background(
            UnevenRoundedRectangle(
                topLeadingRadius: Theme.Metric.sheetCornerRadius,
                topTrailingRadius: Theme.Metric.sheetCornerRadius
            )
            .fill(Theme.Palette.surface)
            .wooLift(radius: 18, y: -4, opacity: 0.08)
        )
        .gesture(
            DragGesture(minimumDistance: 6)
                .onChanged { value in dragOffset = value.translation.height }
                .onEnded { value in
                    // Predicted end position decides the stop, so a flick
                    // lands where the finger was going, not where it stopped.
                    let projected = restingHeight - value.predictedEndTranslation.height
                    let midpoint = (collapsedHeight + expandedHeight) / 2
                    withAnimation(Theme.Motion.standard) {
                        detent = projected > midpoint ? .expanded : .collapsed
                        dragOffset = 0
                    }
                }
        )
        .animation(Theme.Motion.standard, value: detent)
    }
}
