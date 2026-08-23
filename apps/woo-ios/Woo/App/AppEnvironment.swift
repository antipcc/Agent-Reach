import Foundation
import SwiftUI
import WooKit

/// The composition root. This is the only place that decides which AI
/// implementations the app runs on — swap the provider here and every screen
/// follows, because nothing downstream knows the difference.
@MainActor
struct AppEnvironment {
    let library: LibraryModel
    let imageLoader: ImageLoader

    static func live() -> AppEnvironment {
        let store = makeStore()
        let config = AIConfigLoader.load()

        // Mocks first: every flow has to work with no key configured at all.
        let mock = AIProvider.mock(assets: DrawingMockAssets(), latency: .realistic)
        var provider = config.isConfigured ? AIProvider.live(config: config, fallback: mock) : mock

        // Cutouts are the exception — Vision does this on-device for free, and
        // the whole look of the app rests on a clean one.
        if config.backgroundRemovalPath == nil {
            provider = provider.replacingBackgroundRemoval(with: VisionBackgroundRemovalService())
        }

        let service = LibraryService(
            store: store,
            provider: provider,
            palette: CoreImagePaletteExtractor()
        )

        // Cutouts are always real, so they do not count toward "mocked".
        let live = config.isConfigured
        let isTryOnMocked = !live || config.tryOnPath == nil
        let isTurnaroundMocked = !config.isTripoConfigured
            && (!live || (config.modelPath == nil && config.spinPath == nil))
        let anyMocked = isTryOnMocked
            || isTurnaroundMocked
            || !live
            || config.garmentExtractionPath == nil

        return AppEnvironment(
            library: LibraryModel(
                service: service,
                store: store,
                isUsingMockModels: anyMocked,
                isTryOnMocked: isTryOnMocked
            ),
            imageLoader: ImageLoader(store: store)
        )
    }

    /// Previews and UI work: no disk, no permissions, nothing to clean up.
    static func preview(snapshot: LibrarySnapshot = .empty) -> AppEnvironment {
        let store = InMemoryOutfitStore(snapshot: snapshot)
        let service = LibraryService(store: store, provider: .mock(latency: .fast))
        return AppEnvironment(
            library: LibraryModel(
                service: service,
                store: store,
                isUsingMockModels: true,
                isTryOnMocked: true
            ),
            imageLoader: ImageLoader(store: store)
        )
    }

    private static func makeStore() -> any OutfitStore {
        do {
            return FileOutfitStore(root: try FileOutfitStore.defaultRoot())
        } catch {
            // Application Support is unavailable in a handful of restricted
            // states; a session that forgets is better than a launch that fails.
            assertionFailure("Falling back to an in-memory library: \(error)")
            return InMemoryOutfitStore()
        }
    }
}
