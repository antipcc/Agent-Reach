import SwiftUI
import WooKit

/// What the menu opens: what the app is running on and how much is in it.
/// Deliberately plain — it exists so the mock/live state is never a mystery.
struct AboutSheet: View {
    @Environment(LibraryModel.self) private var library

    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            VStack(alignment: .leading, spacing: 6) {
                Text("WOO")
                    .font(Theme.Font.wordmark)
                    .tracking(Theme.Font.wordmarkTracking)
                Text("Your looks, day by day.")
                    .font(Theme.Font.hint)
                    .foregroundStyle(Theme.Palette.inkSecondary)
            }

            Divider().background(Theme.Palette.hairline)

            row("Looks", value: "\(library.outfits.count)")
            row("Pieces", value: "\(library.items.count)")
            row(
                "Image models",
                value: library.isUsingMockModels ? "Partly stand-ins" : "Connected"
            )
            row("Cutouts", value: "On device")
            row("3D looks", value: modelSummary)

            if library.isUsingMockModels {
                Text("Garment splitting, try-on and 3D reconstruction are running on stand-ins. Add an AIConfig.plist or set WOO_AI_* to connect real models.")
                    .font(Theme.Font.itemName)
                    .foregroundStyle(Theme.Palette.inkTertiary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer()
        }
        .padding(24)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.Palette.surface)
    }

    /// Counts what the library actually holds rather than what is configured
    /// — a reconstruction that failed leaves the setting on and the look bare.
    private var modelSummary: String {
        let meshes = library.outfits.filter(\.hasModel)
        guard !meshes.isEmpty else { return "None yet" }
        let standIns = meshes.filter { $0.model?.isPlaceholder == true }.count
        return standIns == 0
            ? "\(meshes.count) reconstructed"
            : "\(meshes.count), \(standIns) stand-in"
    }

    private func row(_ title: String, value: String) -> some View {
        HStack {
            Text(title)
                .font(Theme.Font.date)
                .foregroundStyle(Theme.Palette.inkSecondary)
            Spacer()
            Text(value)
                .font(Theme.Font.date)
                .foregroundStyle(Theme.Palette.ink)
        }
    }
}
