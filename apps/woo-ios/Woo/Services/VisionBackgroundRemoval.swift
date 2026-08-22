import CoreImage
import UIKit
import Vision
import WooKit

/// Real, on-device, free: iOS 17's foreground-instance mask lifts the person
/// out of the photo. This is the one AI service that is not mocked, because
/// the whole look of the app rests on a clean cutout.
struct VisionBackgroundRemovalService: BackgroundRemovalService {
    /// If Vision finds no subject, hand the photo back untouched rather than
    /// failing the capture — a photo on a plain wall is better than nothing.
    var fallsBackToOriginal = true


    func removeBackground(from image: ImageData) async throws -> ImageData {
        guard let uiImage = UIImage(data: image.data), let cgImage = uiImage.cgImage else {
            throw WooError.aiFailed("That photo could not be read.")
        }

        let handler = VNImageRequestHandler(
            cgImage: cgImage,
            orientation: CGImagePropertyOrientation(uiImage.imageOrientation)
        )
        let request = VNGenerateForegroundInstanceMaskRequest()

        do {
            try handler.perform([request])
            guard let result = request.results?.first, !result.allInstances.isEmpty else {
                return try fallback(image, reason: "No one was found in that photo.")
            }
            let masked = try result.generateMaskedImage(
                ofInstances: result.allInstances,
                from: handler,
                croppedToInstancesExtent: true
            )
            guard let png = pngData(from: CIImage(cvPixelBuffer: masked)) else {
                return try fallback(image, reason: "The cutout could not be encoded.")
            }
            return .png(png)
        } catch let error as WooError {
            throw error
        } catch {
            return try fallback(image, reason: error.localizedDescription)
        }
    }

    private func fallback(_ image: ImageData, reason: String) throws -> ImageData {
        guard fallsBackToOriginal else { throw WooError.aiFailed(reason) }
        return image
    }

    private func pngData(from ciImage: CIImage) -> Data? {
        SharedCIContext.shared.context.pngRepresentation(
            of: ciImage,
            format: .RGBA8,
            colorSpace: CGColorSpaceCreateDeviceRGB()
        )
    }
}

extension CGImagePropertyOrientation {
    /// Vision works in Core Graphics orientations; UIImage carries UIKit ones.
    /// Getting this wrong silently produces sideways cutouts.
    init(_ orientation: UIImage.Orientation) {
        switch orientation {
        case .up: self = .up
        case .upMirrored: self = .upMirrored
        case .down: self = .down
        case .downMirrored: self = .downMirrored
        case .left: self = .left
        case .leftMirrored: self = .leftMirrored
        case .right: self = .right
        case .rightMirrored: self = .rightMirrored
        @unknown default: self = .up
        }
    }
}

/// One Core Image context for the whole app: expensive to build, safe to
/// share, and not `Sendable` on its own — hence the explicit promise.
final class SharedCIContext: @unchecked Sendable {
    static let shared = SharedCIContext()
    let context = CIContext()
    private init() {}
}
