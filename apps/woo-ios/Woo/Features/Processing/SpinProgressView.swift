import SwiftUI
import WooKit

/// What a 360° generation looks like while it runs: the figure lit against
/// black, a percentage, and a way out that does not cancel the work.
struct SpinProgressView: View {
    @Environment(LibraryModel.self) private var library

    let job: LibraryModel.SpinJob

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
                        title: "Minimize",
                        systemImage: "chevron.down",
                        tint: Color.white.opacity(0.18)
                    ) {
                        library.minimizeSpin()
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
                    ProgressPill(title: "Creating your 360° look", progress: job.progress)
                    ThinProgressBar(progress: job.progress)
                        .padding(.horizontal, 40)
                    Button("Cancel") { library.cancelSpin() }
                        .font(Theme.Font.hint)
                        .foregroundStyle(.white.opacity(0.6))
                }
                .padding(.bottom, 40)
            }
        }
        .transition(.opacity)
    }
}
