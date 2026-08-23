import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// The composition root for everything AI. Swapping mock for real models is
/// a one-line change at the app's entry point — nothing downstream knows
/// which implementation it is holding.
public struct AIProvider: Sendable {
    public var backgroundRemoval: any BackgroundRemovalService
    public var garmentExtraction: any GarmentExtractionService
    public var tryOn: any TryOnService
    public var modelGeneration: any ModelGenerationService
    public var spin: any SpinService

    public init(
        backgroundRemoval: any BackgroundRemovalService,
        garmentExtraction: any GarmentExtractionService,
        tryOn: any TryOnService,
        modelGeneration: any ModelGenerationService,
        spin: any SpinService
    ) {
        self.backgroundRemoval = backgroundRemoval
        self.garmentExtraction = garmentExtraction
        self.tryOn = tryOn
        self.modelGeneration = modelGeneration
        self.spin = spin
    }

    /// Fully offline provider. Every flow in the app runs end to end on this,
    /// with realistic latency and progress, and no API key anywhere.
    public static func mock(
        assets: any MockAssetLibrary = EchoMockAssets(),
        latency: MockLatency = .realistic
    ) -> AIProvider {
        AIProvider(
            backgroundRemoval: MockBackgroundRemovalService(assets: assets, latency: latency),
            garmentExtraction: MockGarmentExtractionService(assets: assets, latency: latency),
            tryOn: MockTryOnService(assets: assets, latency: latency),
            modelGeneration: MockModelGenerationService(latency: latency),
            spin: MockSpinService(assets: assets, latency: latency)
        )
    }

    /// Real endpoints, configured by `AIConfig`. Any service the config does
    /// not cover falls back to its mock, so a half-filled config still runs.
    public static func live(
        config: AIConfig,
        session: URLSession = .shared,
        fallback: AIProvider? = nil
    ) -> AIProvider {
        let mocked = fallback ?? .mock()
        guard config.isConfigured else { return mocked }
        let http = HTTPAIService(config: config, session: session)
        return AIProvider(
            backgroundRemoval: config.backgroundRemovalPath == nil ? mocked.backgroundRemoval : http,
            garmentExtraction: config.garmentExtractionPath == nil ? mocked.garmentExtraction : http,
            tryOn: config.tryOnPath == nil ? mocked.tryOn : http,
            modelGeneration: config.modelPath == nil ? mocked.modelGeneration : http,
            spin: config.spinPath == nil ? mocked.spin : http
        )
    }

    /// Returns a copy with one service replaced — how the app plugs in the
    /// on-device Vision cutout while leaving the rest mocked.
    public func replacingBackgroundRemoval(with service: any BackgroundRemovalService) -> AIProvider {
        var copy = self
        copy.backgroundRemoval = service
        return copy
    }
}
