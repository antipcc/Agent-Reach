import Foundation

/// Progress in `0...1`. Called on an arbitrary executor — hop to the main
/// actor before touching UI state.
public typealias ProgressHandler = @Sendable (Double) -> Void

/// Lifts the subject out of a photo, leaving a transparent background.
/// Backs every capture: the figure on the home card is this service's output.
public protocol BackgroundRemovalService: Sendable {
    func removeBackground(from image: ImageData) async throws -> ImageData
}

/// One garment recognized inside an outfit photo, already cut out.
public struct ExtractedGarment: Hashable, Sendable {
    public var name: String
    public var category: GarmentCategory
    public var cutout: ImageData
    public var colorHex: String?

    public init(name: String, category: GarmentCategory, cutout: ImageData, colorHex: String? = nil) {
        self.name = name
        self.category = category
        self.cutout = cutout
        self.colorHex = colorHex
    }
}

/// Splits a look into its individual pieces and files them by category —
/// what fills the wardrobe.
public protocol GarmentExtractionService: Sendable {
    func extractGarments(from image: ImageData) async throws -> [ExtractedGarment]
}

/// Puts a set of garments onto a person's photo, keeping their pose and scene.
public protocol TryOnService: Sendable {
    func tryOn(
        person: ImageData,
        garments: [ImageData],
        progress: @escaping ProgressHandler
    ) async throws -> ImageData
}

/// The frames of a 360° turnaround, in order.
public struct SpinResult: Hashable, Sendable {
    public var frames: [ImageData]

    public init(frames: [ImageData]) {
        self.frames = frames
    }
}

/// Generates the turnaround the home card scrubs through.
public protocol SpinService: Sendable {
    func generateSpin(
        from image: ImageData,
        frameCount: Int,
        progress: @escaping ProgressHandler
    ) async throws -> SpinResult
}
