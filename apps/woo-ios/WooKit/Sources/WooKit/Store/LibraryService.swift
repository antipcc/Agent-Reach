import Foundation

/// The use-case layer: everything the app *does*, expressed once, above the
/// store and the AI provider and below the views. Keeping it here (rather
/// than in a view model) is what makes the capture → cutout → wardrobe →
/// try-on pipeline testable without a simulator.
public actor LibraryService {
    public let store: any OutfitStore
    private var provider: AIProvider
    private let palette: any PaletteExtractor

    /// Frames in a turnaround. 36 gives a 10° step — smooth under a drag
    /// without generating an unreasonable number of images.
    public static let defaultSpinFrameCount = 36

    public init(
        store: any OutfitStore,
        provider: AIProvider,
        palette: any PaletteExtractor = EmptyPaletteExtractor()
    ) {
        self.store = store
        self.provider = provider
        self.palette = palette
    }

    /// Swap AI implementations at runtime (mock ⇄ live) without rebuilding
    /// the library or losing state.
    public func setProvider(_ provider: AIProvider) {
        self.provider = provider
    }

    public func snapshot() async throws -> LibrarySnapshot {
        try await store.load()
    }

    // MARK: - Capture

    /// Takes a fresh photo all the way to a saved look: background removed,
    /// palette sampled, original kept for later garment extraction.
    @discardableResult
    public func ingestPhoto(
        _ photo: ImageData,
        date: Date = Date(),
        source: OutfitSource = .camera
    ) async throws -> Outfit {
        let cutout = try await provider.backgroundRemoval.removeBackground(from: photo)

        let cutoutRef = AssetRef.generated(prefix: "cutout", ext: cutout.format.fileExtension)
        let originalRef = AssetRef.generated(prefix: "original", ext: photo.format.fileExtension)
        try await store.writeAsset(cutout.data, ref: cutoutRef)
        try await store.writeAsset(photo.data, ref: originalRef)

        let outfit = Outfit(
            date: date,
            cutout: cutoutRef,
            original: originalRef,
            palette: palette.palette(from: cutout, count: 5),
            source: source
        )
        try await store.addOutfit(outfit)
        return outfit
    }

    // MARK: - Wardrobe

    /// Splits a look into pieces, files them in the wardrobe and links them
    /// back to the outfit. Re-running replaces the previous extraction rather
    /// than piling up duplicates.
    @discardableResult
    public func extractGarments(for outfitID: UUID) async throws -> [GarmentItem] {
        let snapshot = try await store.load()
        guard var outfit = snapshot.outfits.first(where: { $0.id == outfitID }) else {
            throw WooError.outfitNotFound(outfitID)
        }

        // Prefer the untouched photo — more context for the model than a cutout.
        let sourceRef = outfit.original ?? outfit.cutout
        let source = ImageData(
            data: try await store.readAsset(sourceRef),
            format: sourceRef.inferredFormat
        )

        let extracted = try await provider.garmentExtraction.extractGarments(from: source)
        guard !extracted.isEmpty else { return [] }

        for staleID in outfit.itemIDs {
            try? await store.deleteItem(id: staleID)
        }

        var items: [GarmentItem] = []
        for garment in extracted {
            let ref = AssetRef.generated(prefix: "item", ext: garment.cutout.format.fileExtension)
            try await store.writeAsset(garment.cutout.data, ref: ref)
            items.append(
                GarmentItem(
                    name: garment.name,
                    category: garment.category,
                    cutout: ref,
                    colorHex: garment.colorHex ?? palette.palette(from: garment.cutout, count: 1).first,
                    sourceOutfitID: outfit.id
                )
            )
        }

        try await store.addItems(items)
        outfit.itemIDs = items.map(\.id)
        try await store.updateOutfit(outfit)
        return items
    }

    // MARK: - 360°

    /// What "Create 360°" runs. Reconstructs a mesh when a reconstruction
    /// service is available, and falls back to the frame ring when it is not,
    /// so a provider configured only for frames still produces a turnaround.
    @discardableResult
    public func generateTurnaround(
        for outfitID: UUID,
        progress: @escaping ProgressHandler = { _ in }
    ) async throws -> Outfit {
        do {
            return try await generateModel(for: outfitID, progress: progress)
        } catch WooError.aiUnavailable {
            return try await generateSpin(for: outfitID, progress: progress)
        }
    }

    /// Reconstructs the mesh and attaches it to the look, replacing any
    /// earlier one and cleaning up after it.
    @discardableResult
    public func generateModel(
        for outfitID: UUID,
        progress: @escaping ProgressHandler = { _ in }
    ) async throws -> Outfit {
        let snapshot = try await store.load()
        guard var outfit = snapshot.outfits.first(where: { $0.id == outfitID }) else {
            throw WooError.outfitNotFound(outfitID)
        }

        // The cutout, not the original: a reconstruction has no use for the
        // room behind the subject, and every provider charges by the pixel.
        let cutout = ImageData(
            data: try await store.readAsset(outfit.cutout),
            format: outfit.cutout.inferredFormat
        )
        let result = try await provider.modelGeneration.generateModel(from: cutout, progress: progress)

        let ref = AssetRef.generated(prefix: "model", ext: result.format.fileExtension)
        try await store.writeAsset(result.data, ref: ref)

        let previous = outfit.model?.file
        outfit.model = Model3DAsset(
            file: ref,
            format: result.format,
            isPlaceholder: result.isPlaceholder
        )
        try await store.updateOutfit(outfit)
        if let previous {
            await store.deleteAsset(previous)
        }
        return outfit
    }

    /// Generates the frame-ring turnaround and attaches it to the look.
    @discardableResult
    public func generateSpin(
        for outfitID: UUID,
        frameCount: Int = LibraryService.defaultSpinFrameCount,
        progress: @escaping ProgressHandler = { _ in }
    ) async throws -> Outfit {
        let snapshot = try await store.load()
        guard var outfit = snapshot.outfits.first(where: { $0.id == outfitID }) else {
            throw WooError.outfitNotFound(outfitID)
        }

        let cutout = ImageData(
            data: try await store.readAsset(outfit.cutout),
            format: outfit.cutout.inferredFormat
        )
        let result = try await provider.spin.generateSpin(
            from: cutout,
            frameCount: frameCount,
            progress: progress
        )

        var refs: [AssetRef] = []
        for frame in result.frames {
            let ref = AssetRef.generated(prefix: "spin", ext: frame.format.fileExtension)
            try await store.writeAsset(frame.data, ref: ref)
            refs.append(ref)
        }

        // Replace any earlier turnaround, and clean up after it.
        let previous = outfit.spin?.frames ?? []
        outfit.spin = SpinAsset(frames: refs)
        try await store.updateOutfit(outfit)
        for ref in previous {
            await store.deleteAsset(ref)
        }
        return outfit
    }

    // MARK: - Try-on

    /// Dresses `person` in the chosen wardrobe pieces. Returns the rendering
    /// without saving it — the user decides whether to keep it.
    public func tryOn(
        person: ImageData,
        itemIDs: [UUID],
        progress: @escaping ProgressHandler = { _ in }
    ) async throws -> ImageData {
        let snapshot = try await store.load()
        let chosen = itemIDs.compactMap { id in snapshot.items.first { $0.id == id } }
        guard !chosen.isEmpty else {
            throw WooError.aiFailed("Pick at least one piece to try on.")
        }

        var garments: [ImageData] = []
        for item in chosen {
            garments.append(
                ImageData(data: try await store.readAsset(item.cutout), format: item.cutout.inferredFormat)
            )
        }

        return try await provider.tryOn.tryOn(person: person, garments: garments, progress: progress)
    }

    /// Keeps a try-on rendering as a look of its own, linked to the pieces
    /// that made it.
    @discardableResult
    public func saveTryOnResult(
        _ result: ImageData,
        itemIDs: [UUID],
        date: Date = Date(),
        isFavorite: Bool = false
    ) async throws -> Outfit {
        let cutout = try await provider.backgroundRemoval.removeBackground(from: result)
        let ref = AssetRef.generated(prefix: "tryon", ext: cutout.format.fileExtension)
        try await store.writeAsset(cutout.data, ref: ref)

        let outfit = Outfit(
            date: date,
            cutout: ref,
            palette: palette.palette(from: cutout, count: 5),
            itemIDs: itemIDs,
            isFavorite: isFavorite,
            source: .tryOn
        )
        try await store.addOutfit(outfit)
        return outfit
    }

    // MARK: - Edits

    @discardableResult
    public func setFavorite(_ isFavorite: Bool, outfitID: UUID) async throws -> Outfit {
        let snapshot = try await store.load()
        guard var outfit = snapshot.outfits.first(where: { $0.id == outfitID }) else {
            throw WooError.outfitNotFound(outfitID)
        }
        outfit.isFavorite = isFavorite
        try await store.updateOutfit(outfit)
        return outfit
    }

    public func deleteOutfit(id: UUID) async throws {
        try await store.deleteOutfit(id: id)
    }

    public func deleteItem(id: UUID) async throws {
        try await store.deleteItem(id: id)
    }
}
