import AVFoundation
import Combine
import UIKit

/// Thin wrapper over an `AVCaptureSession`: start, flip, shoot.
///
/// Kept away from SwiftUI so the view can stay declarative and so the
/// simulator — which has no camera — can be detected before anything is
/// configured rather than failing at first frame.
@MainActor
final class CameraController: NSObject, ObservableObject {
    enum State: Equatable {
        case idle
        case ready
        case unavailable(String)
    }

    @Published private(set) var state: State = .idle

    let session = AVCaptureSession()
    private let output = AVCapturePhotoOutput()
    private var position: AVCaptureDevice.Position = .back
    private var captureContinuation: CheckedContinuation<UIImage, Error>?

    /// True where no camera exists at all, so the UI can offer the library
    /// instead of a black rectangle.
    var hasCamera: Bool {
        !AVCaptureDevice.DiscoverySession(
            deviceTypes: [.builtInWideAngleCamera],
            mediaType: .video,
            position: .unspecified
        ).devices.isEmpty
    }

    func start() async {
        guard hasCamera else {
            state = .unavailable("This device has no camera. Choose a photo instead.")
            return
        }

        guard await requestAccess() else {
            state = .unavailable("Woo needs camera access. You can grant it in Settings.")
            return
        }

        configureIfNeeded()
        guard state == .ready else { return }

        let session = session
        await Task.detached(priority: .userInitiated) {
            if !session.isRunning { session.startRunning() }
        }.value
    }

    func stop() {
        let session = session
        Task.detached(priority: .utility) {
            if session.isRunning { session.stopRunning() }
        }
    }

    func flip() {
        position = position == .back ? .front : .back
        configure(force: true)
    }

    func capture() async throws -> UIImage {
        guard state == .ready else {
            throw PhotoSaver.SaveError.failed("The camera is not ready yet.")
        }

        let settings = AVCapturePhotoSettings()
        settings.flashMode = .off

        return try await withCheckedThrowingContinuation { continuation in
            captureContinuation = continuation
            output.capturePhoto(with: settings, delegate: self)
        }
    }

    // MARK: - Setup

    private func requestAccess() async -> Bool {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            return true
        case .notDetermined:
            return await AVCaptureDevice.requestAccess(for: .video)
        default:
            return false
        }
    }

    private func configureIfNeeded() {
        guard session.inputs.isEmpty else {
            state = .ready
            return
        }
        configure(force: false)
    }

    private func configure(force: Bool) {
        session.beginConfiguration()
        defer { session.commitConfiguration() }

        if force {
            for input in session.inputs { session.removeInput(input) }
        }

        session.sessionPreset = .photo

        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: position),
              let input = try? AVCaptureDeviceInput(device: device),
              session.canAddInput(input) else {
            state = .unavailable("The camera could not be opened.")
            return
        }
        session.addInput(input)

        if session.canAddOutput(output) && !session.outputs.contains(output) {
            session.addOutput(output)
        }
        state = .ready
    }
}

extension CameraController: AVCapturePhotoCaptureDelegate {
    nonisolated func photoOutput(
        _ output: AVCapturePhotoOutput,
        didFinishProcessingPhoto photo: AVCapturePhoto,
        error: Error?
    ) {
        let result: Result<UIImage, Error>
        if let error {
            result = .failure(error)
        } else if let data = photo.fileDataRepresentation(), let image = UIImage(data: data) {
            result = .success(image)
        } else {
            result = .failure(PhotoSaver.SaveError.failed("The photo could not be read."))
        }

        Task { @MainActor [weak self] in
            guard let continuation = self?.captureContinuation else { return }
            self?.captureContinuation = nil
            continuation.resume(with: result)
        }
    }
}
