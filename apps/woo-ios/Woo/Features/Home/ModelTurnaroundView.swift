import ModelIO
import SceneKit
import SceneKit.ModelIO
import SwiftUI
import UIKit

/// Renders the reconstructed mesh on the home card and turns it with the
/// drag, in place of the frame ring it replaced.
///
/// Camera control is off on purpose: the gesture lives in `OutfitStageView`,
/// so a mesh and a frame ring answer a drag identically. SceneKit's own
/// controller would add pan, zoom and inertia that the frame ring has no
/// answer for.
struct ModelTurnaroundView: UIViewRepresentable {
    let url: URL
    /// Radians about the vertical axis. Zero faces the viewer.
    var yaw: Double
    /// Stand-ins are tinted flat grey so they never read as a reconstruction.
    var isPlaceholder: Bool

    func makeUIView(context: Context) -> SCNView {
        let view = SCNView()
        view.backgroundColor = .clear
        view.isOpaque = false
        view.antialiasingMode = .multisampling4X
        view.allowsCameraControl = false
        view.autoenablesDefaultLighting = true
        context.coordinator.load(url, isPlaceholder: isPlaceholder, into: view)
        return view
    }

    func updateUIView(_ view: SCNView, context: Context) {
        context.coordinator.load(url, isPlaceholder: isPlaceholder, into: view)
        context.coordinator.turntable?.eulerAngles.y = Float(yaw)
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    final class Coordinator {
        private var loadedURL: URL?
        /// The node the drag rotates — everything the file contained, wrapped
        /// so its own transforms are left alone.
        var turntable: SCNNode?

        func load(_ url: URL, isPlaceholder: Bool, into view: SCNView) {
            guard loadedURL != url else { return }
            loadedURL = url
            view.scene = nil
            turntable = nil

            Task { @MainActor in
                // Parsing a mesh is not main-thread work; a few megabytes of
                // geometry would stutter the card as it appears.
                let built = await Task.detached(priority: .userInitiated) {
                    Self.buildScene(url: url, isPlaceholder: isPlaceholder)
                }.value

                // A newer look may have won the race while this one parsed.
                guard let built, self.loadedURL == url else { return }
                view.scene = built.scene
                view.pointOfView = built.camera
                self.turntable = built.turntable
            }
        }

        private struct Built {
            let scene: SCNScene
            let turntable: SCNNode
            let camera: SCNNode
        }

        private static func buildScene(url: URL, isPlaceholder: Bool) -> Built? {
            let asset = MDLAsset(url: url)
            asset.loadTextures()
            let loaded = SCNScene(mdlAsset: asset)

            let scene = SCNScene()
            scene.background.contents = UIColor.clear

            let turntable = SCNNode()
            for child in loaded.rootNode.childNodes {
                child.removeFromParentNode()
                turntable.addChildNode(child)
            }
            guard !turntable.childNodes.isEmpty else { return nil }

            normalize(turntable)
            if isPlaceholder { tintFlat(turntable) }
            scene.rootNode.addChildNode(turntable)

            let camera = SCNNode()
            camera.camera = SCNCamera()
            camera.camera?.zNear = 0.01
            // The figure is normalized to one unit tall, so this framing holds
            // whatever scale the provider happened to export in.
            camera.position = SCNVector3(0, 0, 1.9)
            scene.rootNode.addChildNode(camera)

            return Built(scene: scene, turntable: turntable, camera: camera)
        }

        /// Scales the mesh to one unit tall and moves its pivot to its centre,
        /// so it turns about itself rather than swinging around the origin.
        private static func normalize(_ node: SCNNode) {
            let (minimum, maximum) = node.boundingBox
            let height = max(maximum.y - minimum.y, 0.0001)
            let scale = 1 / height
            node.scale = SCNVector3(scale, scale, scale)
            node.pivot = SCNMatrix4MakeTranslation(
                (minimum.x + maximum.x) / 2,
                (minimum.y + maximum.y) / 2,
                (minimum.z + maximum.z) / 2
            )
        }

        /// The stand-in ships without materials; left alone it renders white
        /// on a white card. Grey also says "not you" at a glance.
        private static func tintFlat(_ node: SCNNode) {
            let material = SCNMaterial()
            material.diffuse.contents = UIColor(white: 0.72, alpha: 1)
            material.roughness.contents = 0.9
            material.lightingModel = .physicallyBased

            node.enumerateHierarchy { child, _ in
                child.geometry?.materials = [material]
            }
        }
    }
}
