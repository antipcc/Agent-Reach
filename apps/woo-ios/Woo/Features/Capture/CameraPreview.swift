import AVFoundation
import SwiftUI

/// Hosts the capture session's preview layer.
struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> PreviewView {
        let view = PreviewView()
        view.videoPreviewLayer.session = session
        view.videoPreviewLayer.videoGravity = .resizeAspectFill
        return view
    }

    func updateUIView(_ uiView: PreviewView, context: Context) {
        uiView.videoPreviewLayer.session = session
    }

    /// A UIView whose backing layer *is* the preview layer, so it resizes with
    /// the view instead of needing manual frame bookkeeping.
    final class PreviewView: UIView {
        override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }

        var videoPreviewLayer: AVCaptureVideoPreviewLayer {
            // Safe by construction: layerClass above guarantees the type.
            layer as! AVCaptureVideoPreviewLayer
        }
    }
}
