import CoreGraphics
import UIKit
import WooKit

/// What the mock provider draws with.
///
/// The point is that mock output still *looks* like the feature: pieces are
/// real crops of the user's own photo, and a 360° look is a turntable
/// illusion built from the cutout. Nothing here is a model — it is stand-in
/// imagery good enough to judge the interaction by, and it disappears the
/// moment real endpoints are configured.
struct DrawingMockAssets: MockAssetLibrary {
    /// Where each kind of piece sits on a full-body shot, as fractions of the
    /// image (left, top, right, bottom).
    private static let bands: [GarmentCategory: CGRect] = [
        .tops: CGRect(x: 0.16, y: 0.16, width: 0.68, height: 0.36),
        .outerwear: CGRect(x: 0.12, y: 0.14, width: 0.76, height: 0.46),
        .bottoms: CGRect(x: 0.18, y: 0.46, width: 0.64, height: 0.38),
        .dresses: CGRect(x: 0.16, y: 0.18, width: 0.68, height: 0.57),
        .shoes: CGRect(x: 0.20, y: 0.82, width: 0.60, height: 0.18),
        .bags: CGRect(x: 0.55, y: 0.40, width: 0.40, height: 0.30),
        .accessories: CGRect(x: 0.28, y: 0.02, width: 0.44, height: 0.18)
    ]

    func cutout(from source: ImageData) -> ImageData {
        // The real cutout comes from Vision; nothing to fake here.
        source
    }

    func garmentCutouts(from source: ImageData, categories: [GarmentCategory]) -> [ImageData] {
        guard let image = UIImage(data: source.data), let cgImage = image.cgImage else {
            return categories.map { _ in source }
        }

        return categories.map { category in
            let band = Self.bands[category] ?? CGRect(x: 0.2, y: 0.2, width: 0.6, height: 0.4)
            let rect = CGRect(
                x: band.minX * CGFloat(cgImage.width),
                y: band.minY * CGFloat(cgImage.height),
                width: band.width * CGFloat(cgImage.width),
                height: band.height * CGFloat(cgImage.height)
            ).integral

            guard let cropped = cgImage.cropping(to: rect),
                  let data = UIImage(cgImage: cropped).pngData() else {
                return source
            }
            return .png(data)
        }
    }

    func tryOnResult(person: ImageData, garments: [ImageData]) -> ImageData {
        guard let personImage = UIImage(data: person.data) else { return person }

        // Grade the photo toward the colours of the chosen pieces. It is not a
        // try-on; it is a visible acknowledgement that the selection mattered,
        // so the flow can be judged without a model behind it.
        let tint = averageColor(of: garments) ?? UIColor.systemGray

        let renderer = UIGraphicsImageRenderer(size: personImage.size)
        let result = renderer.image { context in
            personImage.draw(at: .zero)
            tint.withAlphaComponent(0.16).setFill()
            context.fill(CGRect(origin: .zero, size: personImage.size), blendMode: .softLight)
        }
        return .png(result.pngData() ?? person.data)
    }

    func spinFrames(from source: ImageData, frameCount: Int) -> [ImageData] {
        guard frameCount > 1, let image = UIImage(data: source.data) else {
            return Array(repeating: source, count: max(1, frameCount))
        }

        let size = image.size
        let renderer = UIGraphicsImageRenderer(size: size)

        return (0..<frameCount).map { index in
            let angle = 2 * Double.pi * Double(index) / Double(frameCount)
            let facing = cos(angle)
            // Width follows the cosine, so the figure narrows as it turns and
            // flips once it is past side-on — a plain turntable illusion.
            let horizontalScale = max(0.14, abs(facing))
            let shade = 0.26 * (1 - (facing + 1) / 2)

            let frame = renderer.image { context in
                let cg = context.cgContext
                cg.translateBy(x: size.width / 2, y: 0)
                cg.scaleBy(x: CGFloat(horizontalScale) * (facing < 0 ? -1 : 1), y: 1)
                cg.translateBy(x: -size.width / 2, y: 0)
                image.draw(at: .zero)

                if shade > 0.01 {
                    cg.setBlendMode(.sourceAtop)
                    UIColor.black.withAlphaComponent(shade).setFill()
                    cg.fill(CGRect(origin: .zero, size: size))
                }
            }
            return .png(frame.pngData() ?? source.data)
        }
    }

    private func averageColor(of garments: [ImageData]) -> UIColor? {
        let extractor = CoreImagePaletteExtractor()
        let hexes = garments.compactMap { extractor.palette(from: $0, count: 1).first }
        guard !hexes.isEmpty else { return nil }

        var red = 0.0, green = 0.0, blue = 0.0
        for hex in hexes {
            guard let components = HexColor.components(hex) else { continue }
            red += components.red
            green += components.green
            blue += components.blue
        }
        let count = Double(hexes.count)
        return UIColor(red: red / count, green: green / count, blue: blue / count, alpha: 1)
    }
}
