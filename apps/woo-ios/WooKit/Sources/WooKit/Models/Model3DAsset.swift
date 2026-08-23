import Foundation

/// A real mesh of the look, stored as a file the renderer can open directly.
///
/// This is what "360°" means now: not a ring of pictures, but geometry the
/// home card turns with a camera.
public struct Model3DAsset: Codable, Hashable, Sendable {
    /// Formats iOS can actually open. glTF/GLB is deliberately absent —
    /// Model I/O cannot read it, so a provider must be asked for USDZ.
    public enum Format: String, Codable, Sendable, CaseIterable {
        case usdz, obj, ply

        public var fileExtension: String { rawValue }

        /// Maps a provider's format string onto something loadable, or nil so
        /// the caller can say plainly what to ask the provider for instead.
        public static func loadable(_ raw: String) -> Format? {
            Format(rawValue: raw.lowercased().trimmingCharacters(in: .whitespaces))
        }
    }

    public var file: AssetRef
    public var format: Format
    /// True when this is the built-in stand-in rather than a reconstruction,
    /// so the UI can label it honestly.
    public var isPlaceholder: Bool
    public var createdAt: Date

    public init(
        file: AssetRef,
        format: Format,
        isPlaceholder: Bool = false,
        createdAt: Date = Date()
    ) {
        self.file = file
        self.format = format
        self.isPlaceholder = isPlaceholder
        self.createdAt = createdAt
    }
}
