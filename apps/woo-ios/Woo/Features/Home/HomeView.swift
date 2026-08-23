import SwiftUI
import WooKit

/// The front page: one look at a time on a white wall, its season behind it,
/// and a sheet that opens to show what it is made of.
@MainActor
struct HomeView: View {
    @Environment(LibraryModel.self) private var library

    var onCalendar: () -> Void
    var onMenu: () -> Void
    var onCapture: () -> Void
    var onToast: (String) -> Void

    @State private var detent: SheetDetent = .collapsed
    @State private var pendingDeletion: Outfit?

    private var collapsedHeight: CGFloat { 148 }
    private var expandedHeight: CGFloat { 320 }

    var body: some View {
        VStack(spacing: 0) {
            WordmarkHeader(onCalendar: onCalendar, onMenu: onMenu)

            if let outfit = library.selectedOutfit {
                stage(for: outfit)
            } else {
                EmptyLibraryView(isLoading: library.isLoading, onCapture: onCapture)
            }
        }
        .overlay(alignment: .bottom) {
            if let outfit = library.selectedOutfit {
                BottomSheet(
                    detent: $detent,
                    collapsedHeight: collapsedHeight,
                    expandedHeight: expandedHeight
                ) {
                    OutfitSheetContent(
                        outfit: outfit,
                        isExpanded: detent == .expanded,
                        onCreateTurnaround: { library.startTurnaround(for: outfit) },
                        onDelete: { pendingDeletion = outfit }
                    )
                }
                // Clears the floating nav bar underneath.
                .padding(.bottom, 72)
                .transition(.move(edge: .bottom))
            }
        }
        .confirmationDialog(
            "删除这套穿搭？",
            isPresented: Binding(
                get: { pendingDeletion != nil },
                set: { if !$0 { pendingDeletion = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button("删除", role: .destructive) {
                guard let outfit = pendingDeletion else { return }
                pendingDeletion = nil
                Task {
                    await library.delete(outfit)
                    onToast("已删除")
                }
            }
            Button("再想想", role: .cancel) { pendingDeletion = nil }
        } message: {
            Text("拆出来的单品会留在衣橱里。")
        }
    }

    private func stage(for outfit: Outfit) -> some View {
        ZStack {
            SeasonWatermark(season: outfit.resolvedSeason())
                .padding(.top, 8)

            OutfitStageView(outfit: outfit)

            HStack {
                GlassCircleButton(
                    systemImage: "chevron.left",
                    size: Theme.Metric.chevronSize,
                    tint: library.canShowPrevious ? Theme.Palette.ink : Theme.Palette.inkTertiary
                ) {
                    withAnimation(Theme.Motion.quick) { library.showPrevious() }
                }
                .disabled(!library.canShowPrevious)
                .accessibilityLabel("上一套")

                Spacer()

                GlassCircleButton(
                    systemImage: "chevron.right",
                    size: Theme.Metric.chevronSize,
                    tint: library.canShowNext ? Theme.Palette.ink : Theme.Palette.inkTertiary
                ) {
                    withAnimation(Theme.Motion.quick) { library.showNext() }
                }
                .disabled(!library.canShowNext)
                .accessibilityLabel("下一套")
            }
            .padding(.horizontal, Theme.Metric.screenPadding)
        }
        // Leave room for the sheet and the nav bar below it.
        .padding(.bottom, collapsedHeight + 48)
    }
}

/// The season set oversized behind the figure, clipped by the screen edges
/// exactly as it is in the reference.
struct SeasonWatermark: View {
    let season: Season

    var body: some View {
        GeometryReader { proxy in
            Text(season.watermark)
                .font(Theme.Font.watermark(size: proxy.size.width * 0.26))
                .tracking(proxy.size.width * 0.01)
                .foregroundStyle(Theme.Palette.watermark)
                // One line, at its natural width — wider than the screen for a
                // six-letter season, and clipped at both edges on purpose.
                .lineLimit(1)
                .fixedSize()
                .frame(maxWidth: .infinity)
                .padding(.top, proxy.size.height * 0.06)
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}

/// Nothing captured yet.
struct EmptyLibraryView: View {
    let isLoading: Bool
    var onCapture: () -> Void

    var body: some View {
        VStack(spacing: 18) {
            Spacer()
            if isLoading {
                ProgressView().tint(Theme.Palette.inkTertiary)
            } else {
                Image(systemName: "camera.viewfinder")
                    .font(.system(size: 34, weight: .ultraLight))
                    .foregroundStyle(Theme.Palette.inkTertiary)
                Text("从今天的第一套开始")
                    .font(Theme.Font.date)
                    .foregroundStyle(Theme.Palette.inkSecondary)
                PillButton(title: "拍一张", systemImage: "camera", action: onCapture)
            }
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
