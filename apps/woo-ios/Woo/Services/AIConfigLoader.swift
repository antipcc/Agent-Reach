import Foundation
import WooKit

/// Finds the real-model configuration, if there is one.
///
/// Two sources, both optional, environment last so a scheme can point a build
/// at staging without touching the bundle:
///
/// 1. `AIConfig.plist` in the app bundle — keys `BaseURL`, `APIKey`,
///    `CutoutPath`, `GarmentsPath`, `TryOnPath`, `ModelPath`, `SpinPath`,
///    and `TripoAPIKey` / `TripoModelVersion` for 3D reconstruction.
/// 2. `WOO_AI_*` environment variables.
///
/// With neither, the app runs entirely on mocks. That is a supported state,
/// not a broken one.
enum AIConfigLoader {
    static func load(bundle: Bundle = .main) -> AIConfig {
        let fromEnvironment = AIConfig.fromEnvironment()
        // A Tripo key stands on its own, so the environment wins as soon as it
        // carries either kind of configuration.
        if fromEnvironment.isConfigured || fromEnvironment.isTripoConfigured {
            return fromEnvironment
        }

        guard let url = bundle.url(forResource: "AIConfig", withExtension: "plist"),
              let data = try? Data(contentsOf: url),
              let raw = try? PropertyListSerialization.propertyList(from: data, format: nil),
              let values = raw as? [String: String] else {
            return fromEnvironment
        }

        func value(_ key: String) -> String? {
            guard let value = values[key]?.trimmingCharacters(in: .whitespacesAndNewlines),
                  !value.isEmpty else { return nil }
            return value
        }

        return AIConfig(
            baseURL: value("BaseURL").flatMap(URL.init(string:)),
            apiKey: value("APIKey"),
            backgroundRemovalPath: value("CutoutPath"),
            garmentExtractionPath: value("GarmentsPath"),
            tryOnPath: value("TryOnPath"),
            modelPath: value("ModelPath"),
            spinPath: value("SpinPath"),
            tripoAPIKey: value("TripoAPIKey"),
            tripoBaseURL: value("TripoBaseURL").flatMap(URL.init(string:)),
            tripoModelVersion: value("TripoModelVersion")
        )
    }
}
