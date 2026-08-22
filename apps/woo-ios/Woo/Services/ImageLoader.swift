import SwiftUI
import UIKit
import WooKit

/// Turns an `AssetRef` into a `UIImage`, once. Backed by `NSCache`, which is
/// thread-safe and evicts under pressure — a wardrobe of cutouts is a lot of
/// bitmaps to hold otherwise.
final class ImageLoader: @unchecked Sendable {
    private let store: any OutfitStore
    private let cache = NSCache<NSString, UIImage>()

    init(store: any OutfitStore) {
        self.store = store
        cache.countLimit = 200
    }

    func image(for ref: AssetRef) async -> UIImage? {
        let key = ref.filename as NSString
        if let cached = cache.object(forKey: key) { return cached }

        let url = store.assetURL(ref)
        // Decode off the main thread; a full-body PNG is not cheap.
        var loaded = await Task.detached(priority: .userInitiated) {
            (try? Data(contentsOf: url)).flatMap(UIImage.init(data:))
        }.value

        if loaded == nil, let data = try? await store.readAsset(ref) {
            loaded = UIImage(data: data)
        }

        if let loaded { cache.setObject(loaded, forKey: key) }
        return loaded
    }

    /// Call after overwriting an asset in place so the stale bitmap goes.
    func invalidate(_ ref: AssetRef) {
        cache.removeObject(forKey: ref.filename as NSString)
    }
}

private struct ImageLoaderKey: EnvironmentKey {
    static let defaultValue = ImageLoader(store: InMemoryOutfitStore())
}

extension EnvironmentValues {
    var imageLoader: ImageLoader {
        get { self[ImageLoaderKey.self] }
        set { self[ImageLoaderKey.self] = newValue }
    }
}

/// Draws a stored asset, fading in once it is decoded.
struct AssetImage: View {
    let ref: AssetRef?
    var contentMode: ContentMode = .fit

    @Environment(\.imageLoader) private var loader
    @State private var image: UIImage?

    var body: some View {
        Group {
            if let image {
                Image(uiImage: image)
                    .resizable()
                    .aspectRatio(contentMode: contentMode)
                    .transition(.opacity)
            } else {
                Color.clear
            }
        }
        .task(id: ref?.filename) {
            guard let ref else {
                image = nil
                return
            }
            let loaded = await loader.image(for: ref)
            withAnimation(Theme.Motion.gentle) { image = loaded }
        }
    }
}
