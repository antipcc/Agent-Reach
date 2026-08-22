import CoreGraphics
import UIKit
import WooKit

/// Samples the dots under the card straight off the cutout.
///
/// Deliberately simple: downscale hard, bucket the surviving pixels by colour,
/// and take the most common buckets. Skipping transparent and near-white
/// pixels is what keeps it reporting the clothes rather than the background.
struct CoreImagePaletteExtractor: PaletteExtractor {
    /// Side length the image is squashed to before counting. Small enough to
    /// be instant, large enough that an accessory still registers.
    private let sampleSide = 48

    func palette(from image: ImageData, count: Int) -> [String] {
        guard count > 0,
              let uiImage = UIImage(data: image.data),
              let pixels = downsampledPixels(uiImage) else {
            return []
        }

        var histogram: [UInt32: (count: Int, red: Double, green: Double, blue: Double)] = [:]

        for pixel in pixels {
            guard pixel.alpha > 0.6 else { continue }
            let luminance = 0.299 * pixel.red + 0.587 * pixel.green + 0.114 * pixel.blue
            // Drop paper-white and near-black: neither says anything about a look.
            guard luminance > 0.06, luminance < 0.97 else { continue }

            let key = bucketKey(pixel)
            var entry = histogram[key] ?? (0, 0, 0, 0)
            entry.count += 1
            entry.red += pixel.red
            entry.green += pixel.green
            entry.blue += pixel.blue
            histogram[key] = entry
        }

        return histogram.values
            .sorted { $0.count > $1.count }
            .prefix(count)
            .map { entry in
                HexColor.string(
                    red: entry.red / Double(entry.count),
                    green: entry.green / Double(entry.count),
                    blue: entry.blue / Double(entry.count)
                )
            }
    }

    private struct Pixel {
        let red, green, blue, alpha: Double
    }

    /// Five bits per channel: close shades merge into one dot instead of
    /// filling the row with the same beige four times.
    private func bucketKey(_ pixel: Pixel) -> UInt32 {
        let quantize = { (value: Double) in UInt32(min(max(value, 0), 1) * 7) }
        return quantize(pixel.red) << 8 | quantize(pixel.green) << 4 | quantize(pixel.blue)
    }

    private func downsampledPixels(_ image: UIImage) -> [Pixel]? {
        guard let cgImage = image.cgImage else { return nil }

        let side = sampleSide
        var raw = [UInt8](repeating: 0, count: side * side * 4)
        guard let context = CGContext(
            data: &raw,
            width: side,
            height: side,
            bitsPerComponent: 8,
            bytesPerRow: side * 4,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else {
            return nil
        }

        context.interpolationQuality = .medium
        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: side, height: side))

        return stride(from: 0, to: raw.count, by: 4).map { offset in
            let alpha = Double(raw[offset + 3]) / 255
            // Undo premultiplication so a semi-transparent edge reports its
            // real colour rather than a darkened one.
            let unpremultiply = { (value: UInt8) -> Double in
                alpha > 0 ? min(1, Double(value) / 255 / alpha) : 0
            }
            return Pixel(
                red: unpremultiply(raw[offset]),
                green: unpremultiply(raw[offset + 1]),
                blue: unpremultiply(raw[offset + 2]),
                alpha: alpha
            )
        }
    }
}
