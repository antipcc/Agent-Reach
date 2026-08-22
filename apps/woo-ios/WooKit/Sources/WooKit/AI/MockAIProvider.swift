import Foundation

/// Shared plumbing for the mock services: emit monotonic progress from 0 to 1
/// across `latency.steps`, sleeping between ticks, and honour cancellation.
private func runMockJob(
    latency: MockLatency,
    progress: @escaping ProgressHandler
) async throws {
    progress(0)
    let step = latency.stepDuration
    for tick in 1...latency.steps {
        if step > .zero {
            try await Task.sleep(for: step)
        }
        try Task.checkCancellation()
        progress(Double(tick) / Double(latency.steps))
    }
}

/// Names the mock hands out, per category. Picked to match what the reference
/// app labels its pieces with.
private let mockNames: [GarmentCategory: [String]] = [
    .tops: ["Graphic T-shirt", "Ribbed Camisole", "Sailor Collar Top", "Cropped Tee"],
    .outerwear: ["Cropped Cardigan", "Chambray Shirt", "Quilted Jacket"],
    .bottoms: ["Pleated Mini Skirt", "Wide-leg Cargos", "Denim Shorts", "Tiered Tulle Skirt"],
    .dresses: ["Slip Dress", "Tiered Midi Dress"],
    .shoes: ["Platform Combat Boots", "Chunky Sneakers", "Mary Jane Flats"],
    .bags: ["Fluffy Shoulder Bag", "Mini Tote"],
    .accessories: ["Ribbon Choker", "Baseball Cap", "Leg Warmers"]
]

/// Deterministic pick so the same photo always produces the same wardrobe —
/// mock output that jitters between runs makes the app feel broken.
private func mockName(for category: GarmentCategory, seed: Int) -> String {
    let pool = mockNames[category] ?? [category.displayName.capitalized]
    return pool[abs(seed) % pool.count]
}

private func seed(for image: ImageData) -> Int {
    // Cheap, stable digest of the first bytes — enough to vary names per photo.
    image.data.prefix(64).reduce(into: 7) { partial, byte in
        partial = partial &* 31 &+ Int(byte)
    }
}

public struct MockBackgroundRemovalService: BackgroundRemovalService {
    let assets: any MockAssetLibrary
    let latency: MockLatency

    public init(assets: any MockAssetLibrary = EchoMockAssets(), latency: MockLatency = .fast) {
        self.assets = assets
        self.latency = latency
    }

    public func removeBackground(from image: ImageData) async throws -> ImageData {
        guard !image.isEmpty else { throw WooError.aiFailed("There was no photo to work from.") }
        try await runMockJob(latency: latency) { _ in }
        return assets.cutout(from: image)
    }
}

public struct MockGarmentExtractionService: GarmentExtractionService {
    let assets: any MockAssetLibrary
    let latency: MockLatency

    public init(assets: any MockAssetLibrary = EchoMockAssets(), latency: MockLatency = .fast) {
        self.assets = assets
        self.latency = latency
    }

    public func extractGarments(from image: ImageData) async throws -> [ExtractedGarment] {
        guard !image.isEmpty else { throw WooError.aiFailed("There was no photo to work from.") }
        try await runMockJob(latency: latency) { _ in }

        // A full-body shot reliably yields a top, a bottom and shoes; that is
        // what the reference app surfaces under the card too.
        let categories: [GarmentCategory] = [.tops, .bottoms, .shoes]
        let cutouts = assets.garmentCutouts(from: image, categories: categories)
        let base = seed(for: image)

        return zip(categories, cutouts).enumerated().map { index, pair in
            let (category, cutout) = pair
            return ExtractedGarment(
                name: mockName(for: category, seed: base &+ index),
                category: category,
                cutout: cutout
            )
        }
    }
}

public struct MockTryOnService: TryOnService {
    let assets: any MockAssetLibrary
    let latency: MockLatency

    public init(assets: any MockAssetLibrary = EchoMockAssets(), latency: MockLatency = .realistic) {
        self.assets = assets
        self.latency = latency
    }

    public func tryOn(
        person: ImageData,
        garments: [ImageData],
        progress: @escaping ProgressHandler
    ) async throws -> ImageData {
        guard !person.isEmpty else { throw WooError.aiFailed("Pick a full-body photo first.") }
        guard !garments.isEmpty else { throw WooError.aiFailed("Pick at least one piece to try on.") }
        try await runMockJob(latency: latency, progress: progress)
        return assets.tryOnResult(person: person, garments: garments)
    }
}

public struct MockSpinService: SpinService {
    let assets: any MockAssetLibrary
    let latency: MockLatency

    public init(assets: any MockAssetLibrary = EchoMockAssets(), latency: MockLatency = .realistic) {
        self.assets = assets
        self.latency = latency
    }

    public func generateSpin(
        from image: ImageData,
        frameCount: Int,
        progress: @escaping ProgressHandler
    ) async throws -> SpinResult {
        guard !image.isEmpty else { throw WooError.aiFailed("There was no photo to work from.") }
        guard frameCount > 1 else { throw WooError.aiFailed("A 360° look needs at least two frames.") }
        try await runMockJob(latency: latency, progress: progress)
        return SpinResult(frames: assets.spinFrames(from: image, frameCount: frameCount))
    }
}
