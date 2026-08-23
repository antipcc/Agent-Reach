import SwiftUI
import WooKit

/// What a 360° generation looks like while it runs: the figure lit against
/// black, a percentage, and a way out that does not cancel the work.
///
/// The same screen covers both kinds of turnaround — a mesh reconstruction
/// and the fallback frame ring take comparable time and neither has anything
/// to show until it is done.
struct TurnaroundProgressView: View {
    @Environment(LibraryModel.self) private var library

    let job: LibraryModel.TurnaroundJob

    var body: some View {
        ZStack {
            Theme.Palette.scrim.ignoresSafeArea()

            // A soft pool of light behind the subject, as in the reference.
            RadialGradient(
                colors: [Color.white.opacity(0.16), .clear],
                center: .center,
                startRadius: 10,
                endRadius: 320
            )
            .ignoresSafeArea()

            VStack {
                HStack {
                    PillButton(
                        title: "收起",
                        systemImage: "chevron.down",
                        tint: Color.white.opacity(0.18)
                    ) {
                        library.minimizeTurnaround()
                    }
                    Spacer()
                }
                .padding(.horizontal, Theme.Metric.screenPadding)
                .padding(.top, 8)

                Spacer()

                AssetImage(ref: job.preview)
                    .frame(maxWidth: .infinity)
                    .padding(.horizontal, 60)

                Spacer()

                VStack(spacing: 14) {
                    ProgressPill(title: "正在生成 360° 造型", progress: job.progress)
                    ThinProgressBar(progress: job.progress)
                        .padding(.horizontal, 40)
                    Button("取消") { library.cancelTurnaround() }
                        .font(Theme.Font.hint)
                        .foregroundStyle(.white.opacity(0.6))
                }
                .padding(.bottom, 40)
            }
        }
        .transition(.opacity)
    }
}
