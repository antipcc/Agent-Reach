import SwiftUI
import WooKit

/// The figure itself: draggable around the card, and — once a 360° look
/// exists — turnable, because a horizontal drag scrubs the spin frames.
struct OutfitStageView: View {
    let outfit: Outfit

    /// Points of horizontal travel per frame. Twelve makes a full turn about
    /// a screen-and-a-half wide: enough control to stop at a back view.
    private static let pointsPerFrame: CGFloat = 12

    private enum DragMode {
        case undecided, turning, moving
    }

    @State private var frameIndex = 0
    @State private var offset: CGSize = .zero
    @State private var committedFrame = 0
    @State private var committedOffset: CGSize = .zero
    @State private var mode: DragMode = .undecided

    private var currentRef: AssetRef {
        outfit.spin?.frame(at: frameIndex) ?? outfit.cutout
    }

    var body: some View {
        AssetImage(ref: currentRef)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(.horizontal, 44)
            .offset(offset)
            .gesture(dragGesture)
            .onTapGesture(count: 2) {
                withAnimation(Theme.Motion.standard) {
                    offset = .zero
                    committedOffset = .zero
                }
            }
            .onChange(of: outfit.id) { _, _ in reset() }
            .accessibilityLabel(outfit.hasSpin
                ? "Look with a 360° view. Drag sideways to turn it."
                : "Look. Drag to move it.")
    }

    private var dragGesture: some Gesture {
        DragGesture(minimumDistance: 4)
            .onChanged { value in
                if mode == .undecided {
                    // Lock the axis on the first meaningful movement, so a
                    // turn never drifts and a move never jitters the frame.
                    let horizontal = abs(value.translation.width)
                    let vertical = abs(value.translation.height)
                    mode = (outfit.hasSpin && horizontal > vertical) ? .turning : .moving
                }

                switch mode {
                case .turning:
                    let advanced = Int((value.translation.width / Self.pointsPerFrame).rounded())
                    frameIndex = committedFrame - advanced
                case .moving:
                    offset = CGSize(
                        width: committedOffset.width + value.translation.width,
                        height: committedOffset.height + value.translation.height
                    )
                case .undecided:
                    break
                }
            }
            .onEnded { _ in
                committedFrame = frameIndex
                committedOffset = offset
                mode = .undecided
            }
    }

    private func reset() {
        frameIndex = 0
        committedFrame = 0
        withAnimation(Theme.Motion.quick) {
            offset = .zero
            committedOffset = .zero
        }
    }
}
