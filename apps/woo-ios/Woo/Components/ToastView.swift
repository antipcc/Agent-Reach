import SwiftUI

/// Momentary confirmation — "Saved to favorites". Never carries an action;
/// anything that needs one is not a toast.
struct ToastView: View {
    let message: String

    var body: some View {
        Text(message)
            .font(Theme.Font.hint)
            .foregroundStyle(.white)
            .padding(.horizontal, 18)
            .padding(.vertical, 11)
            .background(Capsule().fill(Color.black.opacity(0.78)))
            .wooLift(radius: 12, y: 4, opacity: 0.18)
            .transition(.opacity.combined(with: .move(edge: .bottom)))
    }
}

/// Presents a toast above whatever it is attached to, and clears it after a
/// beat so no caller has to remember to.
struct ToastHost: ViewModifier {
    @Binding var message: String?
    var bottomInset: CGFloat = 120

    func body(content: Content) -> some View {
        content.overlay(alignment: .bottom) {
            if let message {
                ToastView(message: message)
                    .padding(.bottom, bottomInset)
                    .task(id: message) {
                        try? await Task.sleep(for: .seconds(1.8))
                        withAnimation(Theme.Motion.gentle) { self.message = nil }
                    }
            }
        }
        .animation(Theme.Motion.gentle, value: message)
    }
}

extension View {
    func wooToast(_ message: Binding<String?>, bottomInset: CGFloat = 120) -> some View {
        modifier(ToastHost(message: message, bottomInset: bottomInset))
    }
}
