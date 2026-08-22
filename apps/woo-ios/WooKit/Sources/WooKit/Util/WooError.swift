import Foundation

/// Everything WooKit can fail with, in terms the UI can act on.
public enum WooError: LocalizedError, Sendable, Equatable {
    case assetNotFound(String)
    case outfitNotFound(UUID)
    case itemNotFound(UUID)
    case libraryCorrupted(String)
    case aiUnavailable(String)
    case aiFailed(String)

    public var errorDescription: String? {
        switch self {
        case .assetNotFound(let name):
            return "Image \(name) is missing from the library."
        case .outfitNotFound:
            return "That look is no longer in your library."
        case .itemNotFound:
            return "That piece is no longer in your wardrobe."
        case .libraryCorrupted(let detail):
            return "Your library could not be read: \(detail)"
        case .aiUnavailable(let detail):
            return detail
        case .aiFailed(let detail):
            return detail
        }
    }
}
