import SwiftUI
import WooKit

/// Holds the two places you can be (home, wardrobe), the flows that cover
/// them (capture, dress-up), and the one job that outlives them (360°).
@MainActor
struct RootView: View {
    @Environment(LibraryModel.self) private var library

    @State private var tab: WooTab = .home
    @State private var isCapturing = false
    @State private var isShowingCalendar = false
    @State private var isShowingAbout = false
    @State private var dressUpRequest: DressUpRequest?
    @State private var toast: String?

    var body: some View {
        ZStack(alignment: .bottom) {
            Theme.Palette.ground.ignoresSafeArea()

            content
                .transition(.opacity)

            navigationBar

            if let job = library.turnaroundJob, job.isMinimized {
                minimizedTurnaroundBadge(job)
            }
        }
        .overlay(alignment: .top) {
            if let message = library.errorMessage {
                ErrorBanner(message: message) { library.errorMessage = nil }
            }
        }
        .overlay {
            if let job = library.turnaroundJob, !job.isMinimized {
                TurnaroundProgressView(job: job)
                    .transition(.opacity)
            }
        }
        .animation(Theme.Motion.standard, value: library.turnaroundJob)
        .animation(Theme.Motion.gentle, value: library.errorMessage)
        .wooToast($toast)
        .fullScreenCover(isPresented: $isCapturing) {
            CaptureFlowView { image in
                Task { await library.ingest(image) }
            }
        }
        .fullScreenCover(item: $dressUpRequest) { request in
            DressUpFlowView(itemIDs: request.itemIDs) { message in
                toast = message
            }
        }
        .sheet(isPresented: $isShowingCalendar) {
            CalendarSheet { outfit in
                library.selectedOutfitID = outfit.id
                tab = .home
            }
            .presentationDetents([.medium, .large])
            .presentationDragIndicator(.visible)
        }
        .sheet(isPresented: $isShowingAbout) {
            AboutSheet()
                .presentationDetents([.medium])
                .presentationDragIndicator(.visible)
        }
    }

    @ViewBuilder
    private var content: some View {
        switch tab {
        case .home:
            HomeView(
                onCalendar: { isShowingCalendar = true },
                onMenu: { isShowingAbout = true },
                onCapture: { isCapturing = true },
                onToast: { toast = $0 }
            )
        case .wardrobe:
            WardrobeView { itemIDs in
                dressUpRequest = DressUpRequest(itemIDs: itemIDs)
            }
        }
    }

    private var navigationBar: some View {
        BottomNavBar(tab: $tab) { isCapturing = true }
            .padding(.bottom, 6)
    }

    private func minimizedTurnaroundBadge(_ job: LibraryModel.TurnaroundJob) -> some View {
        Button {
            library.restoreTurnaround()
        } label: {
            HStack(spacing: 8) {
                AssetImage(ref: job.preview)
                    .frame(width: 24, height: 24)
                    .clipShape(Circle())
                Text("360° \(Int((job.progress * 100).rounded()))%")
                    .font(Theme.Font.hint.monospacedDigit())
                    .foregroundStyle(.white)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 9)
            .background(Capsule().fill(Color.black.opacity(0.8)))
            .wooLift(radius: 12, y: 4, opacity: 0.2)
        }
        .buttonStyle(.plain)
        .padding(.bottom, 86)
        .transition(.move(edge: .bottom).combined(with: .opacity))
        .accessibilityLabel("360° 造型生成中，\(Int((job.progress * 100).rounded())) %")
    }
}

/// Identifies one trip through the dress-up flow.
struct DressUpRequest: Identifiable {
    let id = UUID()
    let itemIDs: [UUID]
}

/// Failures surface here rather than in an alert — nothing in this app is
/// worth a modal interruption.
struct ErrorBanner: View {
    let message: String
    var onDismiss: () -> Void

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: "exclamationmark.circle")
                .font(.system(size: 14, weight: .medium))
            Text(message)
                .font(Theme.Font.hint)
                .lineLimit(3)
            Spacer(minLength: 8)
            Button(action: onDismiss) {
                Image(systemName: "xmark")
                    .font(.system(size: 12, weight: .semibold))
            }
            .buttonStyle(.plain)
        }
        .foregroundStyle(.white)
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Theme.Palette.destructive)
        )
        .padding(.horizontal, Theme.Metric.screenPadding)
        .transition(.move(edge: .top).combined(with: .opacity))
    }
}

#Preview {
    let environment = AppEnvironment.preview()
    return RootView()
        .environment(environment.library)
        .environment(\.imageLoader, environment.imageLoader)
}
