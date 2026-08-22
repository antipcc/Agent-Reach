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
                value: library.isUsingMockModels ? "Stand-ins" : "Connected"
            )
            row("Cutouts", value: "On device")

            if library.isUsingMockModels {
                Text("Garment splitting, try-on and 360° are running on stand-ins. Add an AIConfig.plist or set WOO_AI_* to connect real models.")
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
