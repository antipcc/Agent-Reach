import AVFoundation
import SwiftUI

/// The shutter screen: full-bleed preview, a full-body guide, and three
/// controls. Falls back to the photo library wherever there is no camera —
/// which is every simulator.
@MainActor
struct CaptureFlowView: View {
    @Environment(\.dismiss) private var dismiss
    @StateObject private var camera = CameraController()

    var onCapture: (UIImage) -> Void

    @State private var isPickingPhoto = false
    @State private var isShowingHelp = false
    @State private var isCapturing = false

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            switch camera.state {
            case .ready:
                CameraPreview(session: camera.session)
                    .ignoresSafeArea()
                BodyGuideOverlay()
            case .unavailable(let reason):
                unavailable(reason)
            case .idle:
                ProgressView().tint(.white)
            }

            controls
        }
        .task { await camera.start() }
        .onDisappear { camera.stop() }
        .sheet(isPresented: $isPickingPhoto) {
            PhotoPicker { image in
                isPickingPhoto = false
                finish(with: image)
            } onCancel: {
                isPickingPhoto = false
            }
            .ignoresSafeArea()
        }
        .sheet(isPresented: $isShowingHelp) {
            CaptureHelpSheet()
                .presentationDetents([.medium])
                .presentationDragIndicator(.visible)
        }
    }

    private var controls: some View {
        VStack {
            HStack {
                GlassCircleButton(
                    systemImage: "xmark",
                    tint: .white,
                    background: Color.white.opacity(0.18)
                ) { dismiss() }
                .accessibilityLabel("Close")

                Spacer()

                GlassCircleButton(
                    systemImage: "questionmark",
                    tint: .white,
                    background: Color.white.opacity(0.18)
                ) { isShowingHelp = true }
                .accessibilityLabel("Tips for a good photo")
            }
            .padding(.horizontal, Theme.Metric.screenPadding)

            Spacer()

            if camera.state == .ready {
                shutterRow
                    .padding(.bottom, 24)
            }
        }
        .padding(.top, 8)
    }

    private var shutterRow: some View {
        HStack {
            Button { isPickingPhoto = true } label: {
                Image(systemName: "photo.on.rectangle")
                    .font(.system(size: 17, weight: .regular))
                    .foregroundStyle(.white)
                    .frame(width: 44, height: 44)
                    .background(RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(Color.white.opacity(0.18)))
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Choose a photo")

            Spacer()

            Button(action: shoot) {
                ZStack {
                    Circle().fill(.white).frame(width: 68, height: 68)
                    Circle().strokeBorder(.white.opacity(0.6), lineWidth: 2).frame(width: 80, height: 80)
                    if isCapturing {
                        ProgressView().tint(Theme.Palette.ink)
                    }
                }
            }
            .buttonStyle(.plain)
            .disabled(isCapturing)
            .accessibilityLabel("Take the photo")

            Spacer()

            Button { camera.flip() } label: {
                Image(systemName: "arrow.triangle.2.circlepath.camera")
                    .font(.system(size: 17, weight: .regular))
                    .foregroundStyle(.white)
                    .frame(width: 44, height: 44)
                    .background(RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(Color.white.opacity(0.18)))
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Flip camera")
        }
        .padding(.horizontal, 28)
    }

    private func unavailable(_ reason: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "camera.metering.unknown")
                .font(.system(size: 32, weight: .ultraLight))
                .foregroundStyle(.white.opacity(0.7))
            Text(reason)
                .font(Theme.Font.hint)
                .foregroundStyle(.white.opacity(0.8))
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            PillButton(title: "Choose a photo", systemImage: "photo", filled: false) {
                isPickingPhoto = true
            }
        }
    }

    private func shoot() {
        guard !isCapturing else { return }
        isCapturing = true
        Task {
            defer { isCapturing = false }
            guard let image = try? await camera.capture() else { return }
            finish(with: image)
        }
    }

    private func finish(with image: UIImage) {
        onCapture(image)
        dismiss()
    }
}

/// The tall oval and the line of instruction over the preview.
struct BodyGuideOverlay: View {
    var body: some View {
        GeometryReader { proxy in
            let width = proxy.size.width * 0.62
            let height = proxy.size.height * 0.66

            ZStack {
                Ellipse()
                    .strokeBorder(.white.opacity(0.75), lineWidth: 1.2)
                    .frame(width: width, height: height)
                    .position(x: proxy.size.width / 2, y: proxy.size.height * 0.52)

                Text("Fit your full body in frame")
                    .font(Theme.Font.hint)
                    .foregroundStyle(.white)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 8)
                    .background(Capsule().fill(.black.opacity(0.35)))
                    .position(x: proxy.size.width / 2, y: proxy.size.height * 0.14)
            }
        }
        .allowsHitTesting(false)
    }
}

/// What actually makes a good source photo — the cutout and the garment
/// split both depend on it, so it is worth saying plainly.
struct CaptureHelpSheet: View {
    private let tips = [
        ("figure.stand", "Stand so your whole body fits inside the oval."),
        ("light.max", "Even, front-on light keeps edges clean."),
        ("rectangle.on.rectangle.slash", "A plain wall behind you cuts out best."),
        ("camera.metering.center.weighted", "Hold the phone at chest height, level.")
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("A good look photo")
                .font(Theme.Font.monthTitle)
                .foregroundStyle(Theme.Palette.ink)

            ForEach(Array(tips.enumerated()), id: \.offset) { _, tip in
                HStack(spacing: 12) {
                    Image(systemName: tip.0)
                        .font(.system(size: 15, weight: .regular))
                        .foregroundStyle(Theme.Palette.inkSecondary)
                        .frame(width: 24)
                    Text(tip.1)
                        .font(Theme.Font.hint)
                        .foregroundStyle(Theme.Palette.inkSecondary)
                }
            }

            Spacer()
        }
        .padding(24)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.Palette.surface)
    }
}
