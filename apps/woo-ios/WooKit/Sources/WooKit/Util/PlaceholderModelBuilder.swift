import Foundation

/// Builds the stand-in mesh used whenever no reconstruction service is
/// configured.
///
/// It emits Wavefront OBJ, which is plain text — so WooKit stays
/// Foundation-only, the repository carries no binary asset, and the whole
/// generate → store → render pipeline can be exercised offline and in tests.
///
/// The result is a blocky mannequin, deliberately. Nobody will mistake it for
/// a reconstruction of themselves, which is the point: a convincing fake here
/// would be a lie about what the app can currently do.
public enum PlaceholderModelBuilder {
    /// Roughly human proportions, about 1.8 units tall, standing on y = 0 and
    /// facing +Z so a yaw of zero shows the front.
    public static func mannequinOBJ() -> String {
        var builder = OBJBuilder()

        // head, with a small nose so a turn is legible — a symmetric block
        // looks motionless while it rotates
        builder.addBox(center: (0, 1.63, 0), size: (0.20, 0.24, 0.22))
        builder.addBox(center: (0, 1.60, 0.13), size: (0.05, 0.05, 0.05))
        // neck, torso, hips
        builder.addBox(center: (0, 1.46, 0), size: (0.09, 0.08, 0.09))
        builder.addBox(center: (0, 1.16, 0), size: (0.40, 0.54, 0.22))
        builder.addBox(center: (0, 0.84, 0), size: (0.36, 0.16, 0.21))
        // arms
        builder.addBox(center: (-0.26, 1.16, 0), size: (0.11, 0.56, 0.13))
        builder.addBox(center: (0.26, 1.16, 0), size: (0.11, 0.56, 0.13))
        // legs
        builder.addBox(center: (-0.11, 0.40, 0), size: (0.15, 0.78, 0.17))
        builder.addBox(center: (0.11, 0.40, 0), size: (0.15, 0.78, 0.17))
        // feet
        builder.addBox(center: (-0.11, 0.03, 0.04), size: (0.15, 0.06, 0.26))
        builder.addBox(center: (0.11, 0.03, 0.04), size: (0.15, 0.06, 0.26))

        return builder.render(name: "WooPlaceholderMannequin")
    }

    public static func mannequinData() -> Data {
        Data(mannequinOBJ().utf8)
    }
}

/// Minimal OBJ writer: vertices and quad faces, nothing else. Enough for an
/// untextured stand-in, and small enough to read in one sitting.
private struct OBJBuilder {
    private var vertices: [(Double, Double, Double)] = []
    private var faces: [[Int]] = []

    /// Appends an axis-aligned box. OBJ face indices are 1-based and global,
    /// so each box offsets by however many vertices came before it.
    mutating func addBox(center: (Double, Double, Double), size: (Double, Double, Double)) {
        let (cx, cy, cz) = center
        let (hx, hy, hz) = (size.0 / 2, size.1 / 2, size.2 / 2)
        let base = vertices.count

        for (sx, sy, sz) in [
            (-1.0, -1.0, -1.0), (1.0, -1.0, -1.0), (1.0, 1.0, -1.0), (-1.0, 1.0, -1.0),
            (-1.0, -1.0, 1.0), (1.0, -1.0, 1.0), (1.0, 1.0, 1.0), (-1.0, 1.0, 1.0)
        ] {
            vertices.append((cx + sx * hx, cy + sy * hy, cz + sz * hz))
        }

        // Counter-clockwise seen from outside, so normals face out.
        let quads = [
            [4, 3, 2, 1], [5, 6, 7, 8], [1, 2, 6, 5],
            [3, 4, 8, 7], [2, 3, 7, 6], [4, 1, 5, 8]
        ]
        faces.append(contentsOf: quads.map { $0.map { $0 + base } })
    }

    func render(name: String) -> String {
        var lines = ["# \(name) — generated stand-in, not a reconstruction", "o \(name)"]
        for vertex in vertices {
            lines.append(String(format: "v %.4f %.4f %.4f", vertex.0, vertex.1, vertex.2))
        }
        for face in faces {
            lines.append("f " + face.map(String.init).joined(separator: " "))
        }
        return lines.joined(separator: "\n") + "\n"
    }
}
