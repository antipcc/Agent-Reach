import Foundation

/// Points at a binary asset (a cutout PNG, an original photo, one spin frame)
/// living inside the library's `Assets` directory. Only the filename is stored
/// so the library file stays portable across app containers and devices.
public struct AssetRef: Codable, Hashable, Sendable {
    public var filename: String

    public init(filename: String) {
        self.filename = filename
    }

    /// Makes a fresh, collision-free reference, e.g. `cutout-8f3c….png`.
    public static func generated(prefix: String, ext: String = "png") -> AssetRef {
        AssetRef(filename: "\(prefix)-\(UUID().uuidString.lowercased()).\(ext)")
    }

    /// The encoding implied by the extension, defaulting to PNG — every
    /// cutout in the library is PNG because it needs an alpha channel.
    public var inferredFormat: ImageData.Format {
        let ext = filename.split(separator: ".").last.map(String.init)?.lowercased()
        return (ext == "jpg" || ext == "jpeg") ? .jpeg : .png
    }
}
