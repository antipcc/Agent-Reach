import Foundation

/// Where an outfit came from. Used to decide what can be redone — a try-on
/// result has no original photo to re-extract garments from.
public enum OutfitSource: String, Codable, Sendable {
    case camera, library, tryOn
}

/// One day's look: the unit the home card, the calendar grid and the
/// wardrobe all revolve around.
public struct Outfit: Identifiable, Codable, Hashable, Sendable {
    public let id: UUID
    /// The day this look belongs to; the calendar buckets by this.
    public var date: Date
    /// Background-removed PNG — the figure standing on the white card.
    public var cutout: AssetRef
    /// Untouched capture, kept so garments can be re-extracted later.
    public var original: AssetRef?
    /// Up to five hex colors, drawn as dots under the card.
    public var palette: [String]
    /// `nil` means "follow the date"; a value means the user pinned it.
    public var season: Season?
    public var itemIDs: [UUID]
    /// The reconstructed mesh. `nil` until a 360° look has been generated.
    public var model: Model3DAsset?
    /// The older frame-ring turnaround. Still rendered when there is no mesh —
    /// looks captured before reconstruction existed keep working, and a
    /// provider configured for frames but not meshes is a valid setup.
    public var spin: SpinAsset?
    public var isFavorite: Bool
    public var source: OutfitSource

    public init(
        id: UUID = UUID(),
        date: Date = Date(),
        cutout: AssetRef,
        original: AssetRef? = nil,
        palette: [String] = [],
        season: Season? = nil,
        itemIDs: [UUID] = [],
        model: Model3DAsset? = nil,
        spin: SpinAsset? = nil,
        isFavorite: Bool = false,
        source: OutfitSource = .camera
    ) {
        self.id = id
        self.date = date
        self.cutout = cutout
        self.original = original
        self.palette = palette
        self.season = season
        self.itemIDs = itemIDs
        self.model = model
        self.spin = spin
        self.isFavorite = isFavorite
        self.source = source
    }

    /// The watermark to draw: the pinned season, else the one the date implies.
    public func resolvedSeason(calendar: Calendar = .current) -> Season {
        season ?? SeasonResolver.season(for: date, calendar: calendar)
    }

    public var hasModel: Bool { model != nil }

    public var hasSpin: Bool {
        (spin?.frameCount ?? 0) > 1
    }

    /// Whether the figure can be turned at all, by either means.
    public var isTurnable: Bool { hasModel || hasSpin }

    /// Every asset this outfit alone owns. Garment cutouts are excluded on
    /// purpose — those belong to the wardrobe and outlive the outfit.
    public var ownedAssets: [AssetRef] {
        var refs = [cutout]
        if let original { refs.append(original) }
        if let model { refs.append(model.file) }
        refs.append(contentsOf: spin?.frames ?? [])
        return refs
    }
}
