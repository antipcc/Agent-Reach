import SwiftUI
import WooKit

@main
struct WooApp: App {
    @State private var library: LibraryModel
    private let imageLoader: ImageLoader

    init() {
        let environment = AppEnvironment.live()
        _library = State(initialValue: environment.library)
        imageLoader = environment.imageLoader
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(library)
                .environment(\.imageLoader, imageLoader)
                .task { await library.refresh() }
                // The app is a white gallery wall; dark mode would fight it.
                .preferredColorScheme(.light)
        }
    }
}
