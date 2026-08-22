import Foundation

/// Where the mock provider gets its pixels. WooKit cannot draw, so the app
/// layer supplies something that can (it crops and transforms the user's own
/// photo, which is why mock results still look like the real thing).
public protocol MockAssetLibrary: Sendable {
    /// Cutouts to hand back as extracted garments, one per requested category.
    func garmentCutouts(from source: ImageData, categories: [GarmentCategory]) -> [ImageData]
    /// The subject, background removed.
    func cutout(from source: ImageData) -> ImageData
    /// A dressed-up rendering of `person`.
    func tryOnResult(person: ImageData, garments: [ImageData]) -> ImageData
    /// `frameCount` frames of a turnaround.
    func spinFrames(from source: ImageData, frameCount: Int) -> [ImageData]
}

/// Fallback library that just echoes the input. Keeps WooKit self-contained
/// and its tests deterministic; the app overrides it with a drawing one.
public struct EchoMockAssets: MockAssetLibrary {
    public init() {}

    public func garmentCutouts(from source: ImageData, categories: [GarmentCategory]) -> [ImageData] {
        categories.map { _ in source }
    }

    public func cutout(from source: ImageData) -> ImageData { source }

    public func tryOnResult(person: ImageData, garments: [ImageData]) -> ImageData { person }

    public func spinFrames(from source: ImageData, frameCount: Int) -> [ImageData] {
        Array(repeating: source, count: max(1, frameCount))
    }
}

/// How long mock work pretends to take. Tests use `.instant`.
public struct MockLatency: Sendable {
    /// Total wall time a job should occupy.
    public var duration: Duration
    /// How many progress ticks to emit along the way.
    public var steps: Int

    public init(duration: Duration, steps: Int) {
        self.duration = duration
        self.steps = max(1, steps)
    }

    /// Long enough for the progress UI to be legible, short enough to demo.
    public static let realistic = MockLatency(duration: .seconds(6), steps: 40)
    public static let fast = MockLatency(duration: .milliseconds(600), steps: 12)
    public static let instant = MockLatency(duration: .zero, steps: 4)

    var stepDuration: Duration {
        guard steps > 0 else { return .zero }
        return duration / steps
    }
}
