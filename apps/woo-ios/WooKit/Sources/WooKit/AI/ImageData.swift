import Foundation

/// Encoded image bytes plus what they are. WooKit stays Foundation-only so it
/// can be built and tested off-device, which means it never touches UIImage —
/// pixels cross this boundary as bytes.
public struct ImageData: Hashable, Sendable {
    public enum Format: String, Codable, Sendable {
        case png, jpeg

        public var fileExtension: String { rawValue }
        public var mimeType: String { self == .png ? "image/png" : "image/jpeg" }
    }

    public var data: Data
    public var format: Format

    public init(data: Data, format: Format) {
        self.data = data
        self.format = format
    }

    public static func png(_ data: Data) -> ImageData { ImageData(data: data, format: .png) }
    public static func jpeg(_ data: Data) -> ImageData { ImageData(data: data, format: .jpeg) }

    public var isEmpty: Bool { data.isEmpty }
}
