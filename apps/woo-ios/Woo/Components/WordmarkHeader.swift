import SwiftUI

/// The masthead: `WOO` on the left, calendar and menu on the right.
struct WordmarkHeader: View {
    var onCalendar: () -> Void
    var onMenu: () -> Void

    var body: some View {
        HStack {
            Text("WOO")
                .font(Theme.Font.wordmark)
                .tracking(Theme.Font.wordmarkTracking)
                .foregroundStyle(Theme.Palette.ink)
                .accessibilityAddTraits(.isHeader)

            Spacer()

            HStack(spacing: 10) {
                GlassCircleButton(systemImage: "calendar", action: onCalendar)
                    .accessibilityLabel("日历")
                GlassCircleButton(systemImage: "line.3.horizontal", action: onMenu)
                    .accessibilityLabel("菜单")
            }
        }
        .padding(.horizontal, Theme.Metric.screenPadding)
        .padding(.top, 4)
    }
}
