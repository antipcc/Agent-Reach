import Foundation

/// Maps a date to the season watermark on the home card.
///
/// Northern-hemisphere month buckets — the same split the recording shows
/// (an August look reads `SUMMER`). Users can override per outfit via
/// `Outfit.season`, so this only has to be the sensible default.
public enum SeasonResolver {
    public static func season(for date: Date, calendar: Calendar = .current) -> Season {
        season(forMonth: calendar.component(.month, from: date))
    }

    public static func season(forMonth month: Int) -> Season {
        switch month {
        case 3...5: return .spring
        case 6...8: return .summer
        case 9...11: return .fall
        default: return .winter
        }
    }
}
