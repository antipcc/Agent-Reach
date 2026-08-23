import Foundation

/// The one JSON encoder/decoder pair the library is written and read with.
///
/// Dates carry fractional seconds. Plain ISO 8601 truncates to the second, so
/// a look saved and reloaded came back with a date that was *nearly* the one
/// it was created with — a lossy round trip that nothing would notice until
/// something compared two of them.
public enum LibraryCoding {
    public static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .custom { date, encoder in
            var container = encoder.singleValueContainer()
            try container.encode(fractional.string(from: date))
        }
        return encoder
    }()

    public static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { decoder in
            let text = try decoder.singleValueContainer().decode(String.self)
            // Whole-second form second: libraries written before fractional
            // seconds were kept must still open.
            if let date = fractional.date(from: text) ?? whole.date(from: text) {
                return date
            }
            throw DecodingError.dataCorrupted(
                DecodingError.Context(
                    codingPath: decoder.codingPath,
                    debugDescription: "Not an ISO 8601 date: \(text)"
                )
            )
        }
        return decoder
    }()

    private static let fractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static let whole: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()
}
