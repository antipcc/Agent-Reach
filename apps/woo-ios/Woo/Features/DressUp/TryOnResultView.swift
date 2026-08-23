import SwiftUI

/// The rendering, and the three things worth doing with it.
struct TryOnResultView: View {
    let image: UIImage
    /// Mocks produce a stand-in rather than a real try-on; say so rather than
    /// letting the result be mistaken for the model's work.
    let isMockResult: Bool
    var onKeep: () -> Void
    var onDownload: () -> Void
    var onClose: () -> Void

    var body: some View {
        ZStack {
            Theme.Palette.ground.ignoresSafeArea()

            VStack(spacing: 0) {
                HStack {
                    GlassCircleButton(systemImage: "xmark", background: Theme.Palette.surface, action: onClose)
                        .accessibilityLabel("关闭")
                    Spacer()
                }
                .padding(.horizontal, Theme.Metric.screenPadding)
                .padding(.top, 8)

                Spacer()

                Image(uiImage: image)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .padding(.horizontal, 24)

                if isMockResult {
                    Text("这是占位结果 —— 接入换装模型后才是真的。")
                        .font(Theme.Font.itemName)
                        .foregroundStyle(Theme.Palette.inkTertiary)
                        .multilineTextAlignment(.center)
                        .padding(.top, 12)
                        .padding(.horizontal, 40)
                }

                Spacer()

                HStack(spacing: 18) {
                    actionButton(
                        systemImage: "heart.fill",
                        tint: Theme.Palette.favorite,
                        label: "收藏",
                        action: onKeep
                    )
                    actionButton(
                        systemImage: "arrow.down",
                        tint: Theme.Palette.ink,
                        label: "存到相册",
                        action: onDownload
                    )
                    ShareLink(
                        item: Image(uiImage: image),
                        preview: SharePreview("你的新造型", image: Image(uiImage: image))
                    ) {
                        Image(systemName: "square.and.arrow.up")
                            .font(.system(size: 16, weight: .regular))
                            .foregroundStyle(Theme.Palette.ink)
                            .frame(width: 48, height: 48)
                            .background(Circle().fill(Theme.Palette.surface))
                            .wooLift(radius: 8, y: 3, opacity: 0.08)
                    }
                    .accessibilityLabel("分享")
                }
                .padding(.bottom, 40)
            }
        }
    }

    private func actionButton(
        systemImage: String,
        tint: Color,
        label: String,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: 16, weight: .regular))
                .foregroundStyle(tint)
                .frame(width: 48, height: 48)
                .background(Circle().fill(Theme.Palette.surface))
                .wooLift(radius: 8, y: 3, opacity: 0.08)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }
}
