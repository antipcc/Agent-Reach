import Foundation

/// The 360° look: an ordered ring of cutout frames. A horizontal drag on the
/// home card maps to an index in `frames`, so the figure turns with the finger.
public struct SpinAsset: Codable, Hashable, Sendable {
    public var frames: [AssetRef]

    public init(frames: [AssetRef]) {
        self.frames = frames
    }

    public var frameCount: Int { frames.count }

    /// Wraps `index` into the ring so dragging past either end keeps spinning.
    public func frame(at index: Int) -> AssetRef? {
        guard !frames.isEmpty else { return nil }
        let count = frames.count
        let wrapped = ((index % count) + count) % count
        return frames[wrapped]
    }
}
