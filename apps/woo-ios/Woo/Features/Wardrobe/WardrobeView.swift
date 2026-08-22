import SwiftUI
import WooKit

/// Every piece the app has lifted out of a look, filed by kind. Selecting
/// pieces raises the tray that starts a dress-up.
@MainActor
struct WardrobeView: View {
    @Environment(LibraryModel.self) private var library

    var onDressUp: ([UUID]) -> Void

    @State private var selection: [UUID] = []
    @State private var pendingDeletion: GarmentItem?

    private var columns: [GridItem] {
        Array(repeating: GridItem(.flexible(), spacing: 12), count: Theme.Metric.wardrobeColumns)
    }

    var body: some View {
        ZStack(alignment: .top) {
            if library.items.isEmpty {
                emptyState
            } else {
                grid
            }

            if !selection.isEmpty {
                SelectionTray(
                    items: selection.compactMap { id in library.items.first { $0.id == id } },
                    onRemove: { id in
                        withAnimation(Theme.Motion.quick) { selection.removeAll { $0 == id } }
                    },
                    onDressUp: { onDressUp(selection) }
                )
                .padding(.horizontal, 12)
                .padding(.top, 6)
                .transition(.move(edge: .top).combined(with: .opacity))
            }
        }
        .animation(Theme.Motion.standard, value: selection)
        .confirmationDialog(
            "Remove this piece?",
            isPresented: Binding(
                get: { pendingDeletion != nil },
                set: { if !$0 { pendingDeletion = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button("Remove", role: .destructive) {
                guard let item = pendingDeletion else { return }
                pendingDeletion = nil
                selection.removeAll { $0 == item.id }
                Task { await library.deleteItem(item) }
            }
            Button("Keep", role: .cancel) { pendingDeletion = nil }
        }
    }

    private var grid: some View {
        ScrollView {
            LazyVStack(spacing: 0, pinnedViews: []) {
                ForEach(library.itemsByCategory()) { section in
                    VStack(alignment: .leading, spacing: 14) {
                        Text(section.category.displayName)
                            .font(Theme.Font.sectionHeader)
                            .tracking(Theme.Font.sectionTracking)
                            .foregroundStyle(Theme.Palette.ink)
                            .padding(.horizontal, Theme.Metric.screenPadding)

                        LazyVGrid(columns: columns, spacing: 14) {
                            ForEach(section.items) { item in
                                GarmentCell(
                                    item: item,
                                    isSelected: selection.contains(item.id),
                                    onTap: { toggle(item) },
                                    onDelete: { pendingDeletion = item }
                                )
                            }
                        }
                        .padding(.horizontal, Theme.Metric.screenPadding)
                    }
                    .padding(.vertical, 18)
                    .background(Theme.Palette.surface)
                    .overlay(alignment: .bottom) {
                        Rectangle()
                            .fill(Theme.Palette.hairline)
                            .frame(height: 0.5)
                    }
                }
            }
            // Clears the tray at the top and the nav bar at the bottom.
            .padding(.top, selection.isEmpty ? 8 : 92)
            .padding(.bottom, 96)
        }
        .background(Theme.Palette.ground)
    }

    private var emptyState: some View {
        VStack(spacing: 14) {
            Spacer()
            Image(systemName: "tray")
                .font(.system(size: 32, weight: .ultraLight))
                .foregroundStyle(Theme.Palette.inkTertiary)
            Text("Your wardrobe fills itself")
                .font(Theme.Font.date)
                .foregroundStyle(Theme.Palette.inkSecondary)
            Text("Every look you capture is split into pieces and filed here.")
                .font(Theme.Font.hint)
                .foregroundStyle(Theme.Palette.inkTertiary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 48)
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func toggle(_ item: GarmentItem) {
        withAnimation(Theme.Motion.quick) {
            if let index = selection.firstIndex(of: item.id) {
                selection.remove(at: index)
            } else {
                selection.append(item.id)
            }
        }
    }
}

/// One piece on the rail.
struct GarmentCell: View {
    let item: GarmentItem
    let isSelected: Bool
    var onTap: () -> Void
    var onDelete: () -> Void

    var body: some View {
        Button(action: onTap) {
            AssetImage(ref: item.cutout)
                .frame(height: 76)
                .frame(maxWidth: .infinity)
                .padding(6)
                .background(
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(isSelected ? Theme.Palette.ground : .clear)
                )
                .overlay(alignment: .topTrailing) {
                    if isSelected {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.system(size: 15))
                            .foregroundStyle(Theme.Palette.accent)
                            .padding(4)
                    }
                }
        }
        .buttonStyle(.plain)
        .contextMenu {
            Button(role: .destructive, action: onDelete) {
                Label("Remove piece", systemImage: "trash")
            }
        }
        .accessibilityLabel(item.name)
        .accessibilityAddTraits(isSelected ? [.isSelected, .isButton] : .isButton)
    }
}

/// The floating tray of chosen pieces, and the one button that matters.
struct SelectionTray: View {
    let items: [GarmentItem]
    var onRemove: (UUID) -> Void
    var onDressUp: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(items) { item in
                        AssetImage(ref: item.cutout)
                            .frame(width: 44, height: 44)
                            .padding(4)
                            .background(
                                RoundedRectangle(cornerRadius: 10, style: .continuous)
                                    .fill(Color.white.opacity(0.12))
                            )
                            .overlay(alignment: .topTrailing) {
                                Button { onRemove(item.id) } label: {
                                    Image(systemName: "xmark.circle.fill")
                                        .font(.system(size: 14))
                                        .foregroundStyle(.white, .black.opacity(0.5))
                                }
                                .buttonStyle(.plain)
                                .offset(x: 4, y: -4)
                            }
                            .accessibilityLabel("\(item.name), tap the cross to remove")
                    }
                }
                .padding(.vertical, 2)
            }

            Button(action: onDressUp) {
                Text("Dress up")
                    .font(Theme.Font.button)
                    .foregroundStyle(.white)
                    .padding(.horizontal, 18)
                    .padding(.vertical, 11)
                    .background(Capsule().fill(Theme.Palette.accent))
            }
            .buttonStyle(.plain)
        }
        .padding(10)
        .background(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(Color.black.opacity(0.82))
        )
        .wooLift(radius: 16, y: 6, opacity: 0.2)
    }
}
