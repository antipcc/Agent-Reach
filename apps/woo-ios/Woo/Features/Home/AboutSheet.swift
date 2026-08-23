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
                Text("一天一套，记下来。")
                    .font(Theme.Font.hint)
                    .foregroundStyle(Theme.Palette.inkSecondary)
            }

            Divider().background(Theme.Palette.hairline)

            row("穿搭", value: "\(library.outfits.count)")
            row("单品", value: "\(library.items.count)")
            row(
                "图像模型",
                value: library.isUsingMockModels ? "部分占位" : "已接入"
            )
            row("抠图", value: "端上运行")
            row("3D 造型", value: modelSummary)

            if library.isUsingMockModels {
                Text("单品拆解、换装和 3D 重建目前都在跑占位实现。放一个 AIConfig.plist，或设置 WOO_AI_* 环境变量，就能接入真实模型。")
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
        guard !meshes.isEmpty else { return "还没有" }
        let standIns = meshes.filter { $0.model?.isPlaceholder == true }.count
        return standIns == 0
            ? "已重建 \(meshes.count) 套"
            : "共 \(meshes.count) 套，\(standIns) 套是占位"
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
