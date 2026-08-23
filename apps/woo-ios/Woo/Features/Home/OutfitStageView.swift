import SwiftUI
import WooKit

/// The figure itself: draggable around the card, and — once a 360° look
/// exists — turnable, whether that look is a reconstructed mesh or the older
/// ring of frames. Both answer the same drag.
struct OutfitStageView: View {
    @Environment(LibraryModel.self) private var library

    let outfit: Outfit

    /// Points of horizontal travel per frame in the fallback ring. Twelve
    /// makes a full turn about a screen-and-a-half wide: enough control to
    /// stop at a back view.
    private static let pointsPerFrame: CGFloat = 12
    /// A full turn of the mesh costs the same travel as a full ring, so the
    /// two feel identical under the thumb.
    private static let pointsPerTurn: CGFloat = pointsPerFrame * 36

    private enum Turnaround {
        case model(Model3DAsset)
        case frames(SpinAsset)
        case still
    }

    private enum DragMode {
        case undecided, turning, moving
    }

    /// Accumulated horizontal travel, in points. Frames and yaw are both read
    /// off this, so switching representation cannot change the feel.
    @State private var turn: CGFloat = 0
    @State private var committedTurn: CGFloat = 0
    @State private var offset: CGSize = .zero
    @State private var committedOffset: CGSize = .zero
    @State private var mode: DragMode = .undecided

    private var turnaround: Turnaround {
        if let model = outfit.model { return .model(model) }
        if let spin = outfit.spin, spin.frameCount > 1 { return .frames(spin) }
        return .still
    }

    private var yaw: Double {
        -Double(turn / Self.pointsPerTurn) * 2 * .pi
    }

    private var frameIndex: Int {
        -Int((turn / Self.pointsPerFrame).rounded())
    }

    var body: some View {
        content
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
            .accessibilityLabel(accessibilityLabel)
    }

    @ViewBuilder
    private var content: some View {
        switch turnaround {
        case .model(let model):
            ModelTurnaroundView(
                url: library.assetURL(model.file),
                yaw: yaw,
                isPlaceholder: model.isPlaceholder
            )
        case .frames(let spin):
            AssetImage(ref: spin.frame(at: frameIndex) ?? outfit.cutout)
        case .still:
            AssetImage(ref: outfit.cutout)
        }
    }

    private var accessibilityLabel: String {
        switch turnaround {
        case .model(let model):
            return model.isPlaceholder
                ? "占位 3D 人形，左右拖动可以转身。"
                : "3D 造型，左右拖动可以转身。"
        case .frames:
            return "带 360° 视角的穿搭，左右拖动可以转身。"
        case .still:
            return "穿搭照片，拖动可以移动。"
        }
    }

    private var dragGesture: some Gesture {
        DragGesture(minimumDistance: 4)
            .onChanged { value in
                if mode == .undecided {
                    // Lock the axis on the first meaningful movement, so a
                    // turn never drifts and a move never jitters the figure.
                    let horizontal = abs(value.translation.width)
                    let vertical = abs(value.translation.height)
                    mode = (outfit.isTurnable && horizontal > vertical) ? .turning : .moving
                }

                switch mode {
                case .turning:
                    turn = committedTurn + value.translation.width
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
                committedTurn = turn
                committedOffset = offset
                mode = .undecided
            }
    }

    private func reset() {
        turn = 0
        committedTurn = 0
        withAnimation(Theme.Motion.quick) {
            offset = .zero
            committedOffset = .zero
        }
    }
}
