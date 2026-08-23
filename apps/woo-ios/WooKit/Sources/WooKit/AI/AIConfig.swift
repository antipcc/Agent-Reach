import Foundation

/// Where the real models live. Ships empty — fill it in (or drop an
/// `AIConfig.plist` into the app bundle) and the app switches off the mocks.
///
/// `@unchecked Sendable`: every field is a value type. `URL` is one too, but
/// swift-corelibs-foundation has not annotated it, so the implicit conformance
/// warns when WooKit is built off-device.
///
/// Each path is optional on purpose: wire up try-on first and leave the rest
/// mocked if that is the order you get vendors approved in.
public struct AIConfig: Codable, Equatable, @unchecked Sendable {
    public var baseURL: URL?
    public var apiKey: String?

    public var backgroundRemovalPath: String?
    public var garmentExtractionPath: String?
    public var tryOnPath: String?
    /// Single-image reconstruction. Job-based at every provider, so the client
    /// submits, polls, then downloads — see `HTTPAIService`.
    public var modelPath: String?
    public var spinPath: String?

    /// Seconds to allow a single request before giving up.
    public var timeout: TimeInterval
    /// How many times to retry a failed request (exponential backoff).
    public var maxRetries: Int
    /// Total budget for one reconstruction job, which runs for minutes rather
    /// than the seconds a single request takes.
    public var modelTimeout: TimeInterval
    /// Seconds between polls of a running reconstruction job.
    public var modelPollInterval: TimeInterval

    public init(
        baseURL: URL? = nil,
        apiKey: String? = nil,
        backgroundRemovalPath: String? = nil,
        garmentExtractionPath: String? = nil,
        tryOnPath: String? = nil,
        modelPath: String? = nil,
        spinPath: String? = nil,
        timeout: TimeInterval = 120,
        maxRetries: Int = 2,
        modelTimeout: TimeInterval = 600,
        modelPollInterval: TimeInterval = 3
    ) {
        self.baseURL = baseURL
        self.apiKey = apiKey
        self.backgroundRemovalPath = backgroundRemovalPath
        self.garmentExtractionPath = garmentExtractionPath
        self.tryOnPath = tryOnPath
        self.modelPath = modelPath
        self.spinPath = spinPath
        self.timeout = timeout
        self.maxRetries = maxRetries
        self.modelTimeout = modelTimeout
        self.modelPollInterval = modelPollInterval
    }

    public static let empty = AIConfig()

    /// A base URL alone is not enough — without a key every call would 401.
    public var isConfigured: Bool {
        guard baseURL != nil, let apiKey, !apiKey.isEmpty else { return false }
        return backgroundRemovalPath != nil
            || garmentExtractionPath != nil
            || tryOnPath != nil
            || modelPath != nil
            || spinPath != nil
    }

    /// Reads `WOO_AI_BASE_URL` / `WOO_AI_API_KEY` / `WOO_AI_*_PATH`, so a
    /// scheme in Xcode can point the app at staging without a code change.
    public static func fromEnvironment(_ environment: [String: String] = ProcessInfo.processInfo.environment) -> AIConfig {
        AIConfig(
            baseURL: environment["WOO_AI_BASE_URL"].flatMap(URL.init(string:)),
            apiKey: environment["WOO_AI_API_KEY"],
            backgroundRemovalPath: environment["WOO_AI_CUTOUT_PATH"],
            garmentExtractionPath: environment["WOO_AI_GARMENTS_PATH"],
            tryOnPath: environment["WOO_AI_TRYON_PATH"],
            modelPath: environment["WOO_AI_MODEL_PATH"],
            spinPath: environment["WOO_AI_SPIN_PATH"]
        )
    }
}
