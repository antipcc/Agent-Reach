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

/// Names the mock hands out, per category. They appear on the wardrobe
/// screen, so they are written the way the interface is.
private let mockNames: [GarmentCategory: [String]] = [
    .tops: ["印花T恤", "罗纹吊带", "海军领上衣", "短款T恤"],
    .outerwear: ["短款开衫", "水洗牛仔衬衫", "绗缝外套"],
    .bottoms: ["百褶短裙", "阔腿工装裤", "牛仔短裤", "多层纱裙"],
    .dresses: ["吊带连衣裙", "多层中长裙"],
    .shoes: ["厚底马丁靴", "老爹鞋", "玛丽珍鞋"],
    .bags: ["毛绒单肩包", "迷你托特包"],
    .accessories: ["蝴蝶结颈带", "棒球帽", "堆堆袜"]
]

/// Deterministic pick so the same photo always produces the same wardrobe —
/// mock output that jitters between runs makes the app feel broken.
private func mockName(for category: GarmentCategory, seed: Int) -> String {
    let pool = mockNames[category] ?? [category.displayName]
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
        guard !image.isEmpty else { throw WooError.aiFailed("没有可用的照片。") }
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
        guard !image.isEmpty else { throw WooError.aiFailed("没有可用的照片。") }
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
        guard !person.isEmpty else { throw WooError.aiFailed("先选一张全身照。") }
        guard !garments.isEmpty else { throw WooError.aiFailed("至少选一件单品来试穿。") }
        try await runMockJob(latency: latency, progress: progress)
        return assets.tryOnResult(person: person, garments: garments)
    }
}

public struct MockModelGenerationService: ModelGenerationService {
    let latency: MockLatency

    public init(latency: MockLatency = .realistic) {
        self.latency = latency
    }

    public func generateModel(
        from image: ImageData,
        progress: @escaping ProgressHandler
    ) async throws -> Model3DResult {
        guard !image.isEmpty else { throw WooError.aiFailed("没有可用的照片。") }
        try await runMockJob(latency: latency, progress: progress)
        return Model3DResult(
            data: PlaceholderModelBuilder.mannequinData(),
            format: .obj,
            isPlaceholder: true
        )
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
        guard !image.isEmpty else { throw WooError.aiFailed("没有可用的照片。") }
        guard frameCount > 1 else { throw WooError.aiFailed("360° 造型至少需要两帧。") }
        try await runMockJob(latency: latency, progress: progress)
        return SpinResult(frames: assets.spinFrames(from: image, frameCount: frameCount))
    }
}
