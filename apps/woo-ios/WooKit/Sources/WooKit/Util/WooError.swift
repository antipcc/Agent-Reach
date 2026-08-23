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
            return "图片 \(name) 已不在图库里了。"
        case .outfitNotFound:
            return "这套穿搭已经不在你的图库里了。"
        case .itemNotFound:
            return "这件单品已经不在你的衣橱里了。"
        case .libraryCorrupted(let detail):
            return "读不出你的图库：\(detail)"
        case .aiUnavailable(let detail):
            return detail
        case .aiFailed(let detail):
            return detail
        }
    }
}
