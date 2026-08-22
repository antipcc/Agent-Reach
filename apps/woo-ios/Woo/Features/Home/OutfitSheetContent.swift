import SwiftUI
import WooKit

/// What sits under the card: the look's colours and date when collapsed, the
/// pieces it is made of when pulled up, and the three things you can do to it.
struct OutfitSheetContent: View {
    @Environment(LibraryModel.self) private var library

    let outfit: Outfit
    let isExpanded: Bool
    var onCreateSpin: () -> Void
    var onDelete: () -> Void

    private static let dateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy.MM.dd"
        return formatter
    }()

    private var pieces: [GarmentItem] {
        library.items(in: outfit)
    }

    var body: some View {
        VStack(spacing: 18) {
            HStack {
                PaletteDotsRow(hexes: outfit.palette)
                Spacer()
                Label(
                    Self.dateFormatter.string(from: outfit.date),
                    systemImage: "calendar"
                )
                .font(Theme.Font.date)
                .foregroundStyle(Theme.Palette.ink)
                .labelStyle(.titleAndIcon)
            }
            .padding(.horizontal, Theme.Metric.screenPadding)

            if isExpanded {
                piecesRow
                    .transition(.opacity.combined(with: .move(edge: .bottom)))
            }

            actions

            Spacer(minLength: 0)
        }
    }

    @ViewBuilder
    private var piecesRow: some View {
        if pieces.isEmpty {
            Text("No pieces were found in this look.")
                .font(Theme.Font.hint)
                .foregroundStyle(Theme.Palette.inkTertiary)
                .frame(height: 118)
        } else {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(pieces) { piece in
                        VStack(spacing: 6) {
                            AssetImage(ref: piece.cutout)
                                .frame(width: 86, height: 86)
                                .padding(6)
                                .background(
                                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                                        .fill(Theme.Palette.ground)
                                )
                            Text(piece.name)
                                .font(Theme.Font.itemName)
                                .foregroundStyle(Theme.Palette.inkSecondary)
                                .lineLimit(1)
                                .truncationMode(.tail)
                                .frame(width: 98)
                        }
                    }
                }
                .padding(.horizontal, Theme.Metric.screenPadding)
            }
            .frame(height: 118)
        }
    }

    private var actions: some View {
        HStack(spacing: 14) {
            if outfit.hasSpin {
                Label("360° ready", systemImage: "rotate.3d")
                    .font(Theme.Font.button)
                    .foregroundStyle(Theme.Palette.inkSecondary)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(Capsule().fill(Theme.Palette.ground))
            } else {
                PillButton(
                    title: "Create 360°",
                    systemImage: "rotate.3d",
                    action: onCreateSpin
                )
                .disabled(library.spinJob != nil)
                .opacity(library.spinJob == nil ? 1 : 0.5)
            }

            ShareLink(item: library.assetURL(outfit.cutout)) {
                Image(systemName: "square.and.arrow.up")
                    .font(.system(size: 15, weight: .regular))
                    .foregroundStyle(Theme.Palette.ink)
                    .frame(width: 40, height: 40)
                    .background(Circle().fill(Theme.Palette.ground))
            }
            .accessibilityLabel("Share this look")

            Button(action: onDelete) {
                Image(systemName: "trash")
                    .font(.system(size: 15, weight: .regular))
                    .foregroundStyle(Theme.Palette.ink)
                    .frame(width: 40, height: 40)
                    .background(Circle().fill(Theme.Palette.ground))
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Delete this look")
        }
    }
}
