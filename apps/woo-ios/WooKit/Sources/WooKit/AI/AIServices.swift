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

/// A reconstructed mesh, as the bytes of a file iOS can open.
public struct Model3DResult: Hashable, Sendable {
    public var data: Data
    public var format: Model3DAsset.Format
    /// Set by the mock so the UI can say the mesh is a stand-in.
    public var isPlaceholder: Bool

    public init(data: Data, format: Model3DAsset.Format, isPlaceholder: Bool = false) {
        self.data = data
        self.format = format
        self.isPlaceholder = isPlaceholder
    }
}

/// Reconstructs a 3D model of the look from a single photo — what "Create
/// 360°" now produces.
///
/// Reconstruction is slow (tens of seconds) and job-based at every provider
/// worth using, hence the progress handler rather than a bare return.
public protocol ModelGenerationService: Sendable {
    func generateModel(
        from image: ImageData,
        progress: @escaping ProgressHandler
    ) async throws -> Model3DResult
}

/// Generates the frame-ring turnaround, kept as the fallback for when no
/// reconstruction endpoint is configured.
public protocol SpinService: Sendable {
    func generateSpin(
        from image: ImageData,
        frameCount: Int,
        progress: @escaping ProgressHandler
    ) async throws -> SpinResult
}
