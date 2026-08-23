import SwiftUI
import WooKit

/// Pick a full-body photo, watch the model work, keep the result. One screen
/// with three states rather than three pushed screens, because it is one act.
@MainActor
struct DressUpFlowView: View {
    @Environment(LibraryModel.self) private var library
    @Environment(\.dismiss) private var dismiss

    let itemIDs: [UUID]
    var onToast: (String) -> Void

    private enum Stage {
        case picking
        case working
        case result(UIImage)
    }

    @State private var stage: Stage = .picking
    @State private var progress: Double = 0
    @State private var person: UIImage?
    @State private var isPickerPresented = false
    @State private var work: Task<Void, Never>?

    private var pieces: [GarmentItem] {
        itemIDs.compactMap { id in library.items.first { $0.id == id } }
    }

    var body: some View {
        ZStack {
            Theme.Palette.ground.ignoresSafeArea()

            switch stage {
            case .picking:
                Color.clear
            case .working:
                workingView
            case .result(let image):
                TryOnResultView(
                    image: image,
                    isMockResult: library.isTryOnMocked,
                    onKeep: { keep(image) },
                    onDownload: { download(image) },
                    onClose: { dismiss() }
                )
            }

            if case .working = stage {
                closeButton
            }
        }
        .onAppear { isPickerPresented = true }
        .onDisappear { work?.cancel() }
        .sheet(isPresented: $isPickerPresented) {
            PhotoPicker { image in
                isPickerPresented = false
                start(with: image)
            } onCancel: {
                isPickerPresented = false
                dismiss()
            }
            .ignoresSafeArea()
        }
    }

    private var closeButton: some View {
        VStack {
            HStack {
                GlassCircleButton(
                    systemImage: "xmark",
                    tint: Theme.Palette.ink,
                    background: Theme.Palette.surface
                ) {
                    work?.cancel()
                    dismiss()
                }
                .accessibilityLabel("取消")
                Spacer()
            }
            .padding(.horizontal, Theme.Metric.screenPadding)
            .padding(.top, 8)
            Spacer()
        }
    }

    private var workingView: some View {
        VStack {
            Spacer()

            if let person {
                Image(uiImage: person)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .clipShape(RoundedRectangle(cornerRadius: Theme.Metric.cardCornerRadius, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: Theme.Metric.cardCornerRadius, style: .continuous)
                            .fill(Color.black.opacity(0.35))
                    )
                    .padding(.horizontal, 44)
            }

            ProgressPill(title: progressTitle, progress: nil)
                .padding(.top, 22)

            Spacer()

            piecesStrip
                .padding(.bottom, 34)
        }
    }

    /// Past the halfway mark the wait is long enough to be worth explaining.
    private var progressTitle: String {
        progress < 0.55 ? "正在生成新造型" : "快好了，先别退出 App"
    }

    private var piecesStrip: some View {
        HStack(spacing: 10) {
            ForEach(pieces) { piece in
                AssetImage(ref: piece.cutout)
                    .frame(width: 42, height: 42)
                    .padding(5)
                    .background(Circle().fill(Theme.Palette.surface))
                    .wooLift(radius: 6, y: 2, opacity: 0.08)
            }
        }
    }

    private func start(with image: UIImage) {
        person = image
        progress = 0
        stage = .working

        work = Task {
            let result = await library.tryOn(person: image, itemIDs: itemIDs) { value in
                Task { @MainActor in progress = value }
            }
            guard !Task.isCancelled else { return }
            if let result {
                stage = .result(result)
            } else {
                // The failure is already on the banner; do not strand the user here.
                dismiss()
            }
        }
    }

    private func keep(_ image: UIImage) {
        Task {
            await library.saveTryOnResult(image, itemIDs: itemIDs)
            onToast("已收藏")
            dismiss()
        }
    }

    private func download(_ image: UIImage) {
        Task {
            do {
                try await PhotoSaver.save(image)
                onToast("已存到相册")
            } catch {
                library.errorMessage = (error as? LocalizedError)?.errorDescription
                    ?? error.localizedDescription
            }
        }
    }
}
