import SwiftUI

/// The three places the app has: today's looks, the shutter, the wardrobe.
enum WooTab: Hashable {
    case home, wardrobe
}

/// Floating capsule bar. The shutter sits in the middle as a filled dark
/// circle because capture is the one thing the app wants you to do.
struct BottomNavBar: View {
    @Binding var tab: WooTab
    var onCapture: () -> Void

    var body: some View {
        HStack(spacing: 26) {
            tabButton(.home, systemImage: "house.fill", label: "首页")

            Button(action: onCapture) {
                Image(systemName: "camera.fill")
                    .font(.system(size: 17, weight: .medium))
                    .foregroundStyle(.white)
                    .frame(width: 46, height: 46)
                    .background(Circle().fill(Theme.Palette.ink))
                    .wooLift(radius: 10, y: 4, opacity: 0.22)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("拍照")

            tabButton(.wardrobe, systemImage: "tray.full.fill", label: "衣橱")
        }
        .padding(.horizontal, 22)
        .padding(.vertical, 8)
        .background(
            Capsule().fill(Theme.Palette.surface)
        )
        .wooLift(radius: 16, y: 6, opacity: 0.1)
    }

    private func tabButton(_ target: WooTab, systemImage: String, label: String) -> some View {
        Button {
            withAnimation(Theme.Motion.quick) { tab = target }
        } label: {
            Image(systemName: systemImage)
                .font(.system(size: 15, weight: .medium))
                .foregroundStyle(tab == target ? Theme.Palette.ink : Theme.Palette.inkTertiary)
                .frame(width: 46, height: 38)
                .background(
                    Capsule()
                        .fill(tab == target ? Theme.Palette.ground : .clear)
                )
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
        .accessibilityAddTraits(tab == target ? [.isSelected, .isButton] : .isButton)
    }
}
