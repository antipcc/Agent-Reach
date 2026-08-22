import Photos
import UIKit

/// Writes a rendering to the user's photo library — the ↓ under a try-on
/// result. Asks for add-only access, which is the least the task needs.
enum PhotoSaver {
    enum SaveError: LocalizedError {
        case denied
        case failed(String)

        var errorDescription: String? {
            switch self {
            case .denied:
                return "Woo needs permission to add photos. You can grant it in Settings."
            case .failed(let detail):
                return detail
            }
        }
    }

    static func save(_ image: UIImage) async throws {
        let status = await PHPhotoLibrary.requestAuthorization(for: .addOnly)
        guard status == .authorized || status == .limited else { throw SaveError.denied }

        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            PHPhotoLibrary.shared().performChanges {
                PHAssetChangeRequest.creationRequestForAsset(from: image)
            } completionHandler: { success, error in
                if success {
                    continuation.resume()
                } else {
                    continuation.resume(throwing: SaveError.failed(
                        error?.localizedDescription ?? "The photo could not be saved."
                    ))
                }
            }
        }
    }
}
