import PhotosUI
import SwiftUI

/// The system photo picker, returning one image. Uses `PHPickerViewController`
/// so it needs no library permission at all.
struct PhotoPicker: UIViewControllerRepresentable {
    var onPick: (UIImage) -> Void
    var onCancel: () -> Void

    func makeUIViewController(context: Context) -> PHPickerViewController {
        var configuration = PHPickerConfiguration()
        configuration.filter = .images
        configuration.selectionLimit = 1

        let controller = PHPickerViewController(configuration: configuration)
        controller.delegate = context.coordinator
        return controller
    }

    func updateUIViewController(_ controller: PHPickerViewController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onPick: onPick, onCancel: onCancel)
    }

    final class Coordinator: NSObject, PHPickerViewControllerDelegate {
        private let onPick: (UIImage) -> Void
        private let onCancel: () -> Void

        init(onPick: @escaping (UIImage) -> Void, onCancel: @escaping () -> Void) {
            self.onPick = onPick
            self.onCancel = onCancel
        }

        func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
            guard let provider = results.first?.itemProvider,
                  provider.canLoadObject(ofClass: UIImage.self) else {
                onCancel()
                return
            }

            provider.loadObject(ofClass: UIImage.self) { [onPick, onCancel] object, _ in
                Task { @MainActor in
                    if let image = object as? UIImage {
                        onPick(image)
                    } else {
                        onCancel()
                    }
                }
            }
        }
    }
}
