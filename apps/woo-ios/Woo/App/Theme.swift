import SwiftUI

/// Every colour, type style and metric the app draws with, in one place.
/// The look is a white gallery wall: paper-white ground, a single ink, and
/// hairlines instead of borders — so the cutout is the only thing with weight.
enum Theme {
    // MARK: - Colour

    enum Palette {
        /// The page behind everything. Warm white, not device white.
        static let ground = Color(red: 0.976, green: 0.976, blue: 0.973)
        /// Cards, sheets, the nav bar.
        static let surface = Color.white
        static let ink = Color(red: 0.106, green: 0.106, blue: 0.106)
        static let inkSecondary = Color(red: 0.42, green: 0.42, blue: 0.42)
        static let inkTertiary = Color(red: 0.65, green: 0.65, blue: 0.65)
        /// The oversized season word behind the figure.
        static let watermark = Color(red: 0.898, green: 0.894, blue: 0.886)
        static let hairline = Color(red: 0.925, green: 0.922, blue: 0.914)
        /// Reserved for the one committing action on screen — "Dress up".
        static let accent = Color(red: 0.04, green: 0.52, blue: 1.0)
        static let destructive = Color(red: 0.85, green: 0.25, blue: 0.25)
        static let favorite = Color(red: 0.92, green: 0.35, blue: 0.42)
        /// Scrim behind full-screen generation.
        static let scrim = Color.black.opacity(0.92)
    }

    // MARK: - Type

    enum Font {
        /// `WOO` — light and widely tracked, the way a masthead is set.
        static let wordmark = SwiftUI.Font.system(size: 22, weight: .light)
        static let wordmarkTracking: CGFloat = 5

        /// The season word. Big enough to bleed past the card edges.
        static func watermark(size: CGFloat) -> SwiftUI.Font {
            .system(size: size, weight: .heavy)
        }

        static let sectionHeader = SwiftUI.Font.system(size: 13, weight: .semibold)
        static let sectionTracking: CGFloat = 1.4

        static let monthTitle = SwiftUI.Font.system(size: 20, weight: .semibold)
        static let date = SwiftUI.Font.system(size: 14, weight: .medium)
        static let itemName = SwiftUI.Font.system(size: 10, weight: .regular)
        static let button = SwiftUI.Font.system(size: 14, weight: .medium)
        static let hint = SwiftUI.Font.system(size: 13, weight: .medium)
    }

    // MARK: - Metrics

    enum Metric {
        static let screenPadding: CGFloat = 20
        static let sheetCornerRadius: CGFloat = 28
        static let cardCornerRadius: CGFloat = 20
        static let controlSize: CGFloat = 38
        static let chevronSize: CGFloat = 34
        static let paletteDot: CGFloat = 11
        static let grabberWidth: CGFloat = 38
        static let grabberHeight: CGFloat = 4
        /// Wardrobe grid: four pieces across, the way a rail reads.
        static let wardrobeColumns = 4
    }

    // MARK: - Motion

    enum Motion {
        /// The house spring. Used for sheets, page turns and selection.
        static let standard = Animation.spring(response: 0.38, dampingFraction: 0.86)
        static let quick = Animation.spring(response: 0.24, dampingFraction: 0.9)
        static let gentle = Animation.easeInOut(duration: 0.25)
    }
}

extension View {
    /// The soft lift used by every floating control — never a hard border.
    func wooLift(radius: CGFloat = 12, y: CGFloat = 4, opacity: Double = 0.08) -> some View {
        shadow(color: .black.opacity(opacity), radius: radius, x: 0, y: y)
    }
}
