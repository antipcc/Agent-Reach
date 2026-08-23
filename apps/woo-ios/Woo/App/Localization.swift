import Foundation

/// The interface is Chinese regardless of what the device is set to, so
/// anything the system would otherwise localize has to be pinned here.
///
/// One shared calendar rather than one per view: the weekday header and the
/// day cells both derive from it, and two independently configured copies
/// would be exactly how a header ends up one column out of step with its grid.
enum Localization {
    static let locale = Locale(identifier: "zh_Hans_CN")

    static let calendar: Calendar = {
        var calendar = Calendar(identifier: .gregorian)
        calendar.locale = locale
        return calendar
    }()

    /// `2026年8月`
    static let monthFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = locale
        formatter.calendar = calendar
        formatter.dateFormat = "yyyy年M月"
        return formatter
    }()

    /// `2026.08.21` — digits, so it reads the same in any language.
    static let dayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = locale
        formatter.calendar = calendar
        formatter.dateFormat = "yyyy.MM.dd"
        return formatter
    }()
}
