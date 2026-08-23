import SwiftUI
import WooKit

/// The month, with the day's look in the day's cell. Tapping a day jumps the
/// home card to it.
struct CalendarSheet: View {
    @Environment(LibraryModel.self) private var library
    @Environment(\.dismiss) private var dismiss

    var onSelect: (Outfit) -> Void

    @State private var visibleMonth = Date()

    private let calendar = Localization.calendar

    var body: some View {
        VStack(spacing: 18) {
            header
            weekdayRow
            monthGrid
            Spacer(minLength: 0)
        }
        .padding(.top, 18)
        .background(Theme.Palette.surface)
    }

    private var header: some View {
        HStack {
            GlassCircleButton(systemImage: "chevron.left", background: Theme.Palette.ground) {
                withAnimation(Theme.Motion.quick) { shiftMonth(by: -1) }
            }
            .accessibilityLabel("上一月")

            Spacer()

            Text(Localization.monthFormatter.string(from: visibleMonth))
                .font(Theme.Font.monthTitle)
                .foregroundStyle(Theme.Palette.ink)

            Spacer()

            GlassCircleButton(systemImage: "chevron.right", background: Theme.Palette.ground) {
                withAnimation(Theme.Motion.quick) { shiftMonth(by: 1) }
            }
            .accessibilityLabel("下一月")
        }
        .padding(.horizontal, Theme.Metric.screenPadding)
    }

    private var weekdayRow: some View {
        HStack(spacing: 0) {
            ForEach(Array(weekdaySymbols.enumerated()), id: \.offset) { _, symbol in
                Text(symbol)
                    .font(Theme.Font.itemName)
                    .foregroundStyle(Theme.Palette.inkTertiary)
                    .frame(maxWidth: .infinity)
            }
        }
        .padding(.horizontal, 12)
    }

    private var monthGrid: some View {
        LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 2), count: 7), spacing: 2) {
            ForEach(Array(days.enumerated()), id: \.offset) { _, day in
                if let day {
                    DayCell(
                        day: day,
                        outfit: library.outfit(on: day, calendar: calendar),
                        isToday: calendar.isDateInToday(day)
                    ) { outfit in
                        onSelect(outfit)
                        dismiss()
                    }
                } else {
                    Color.clear.frame(height: 62)
                }
            }
        }
        .padding(.horizontal, 12)
    }

    /// Single-letter symbols starting on the calendar's own first weekday.
    private var weekdaySymbols: [String] {
        let symbols = calendar.veryShortStandaloneWeekdaySymbols
        let offset = calendar.firstWeekday - 1
        return Array(symbols[offset...] + symbols[..<offset])
    }

    /// The month's days, padded at the front so the first lands in its column.
    private var days: [Date?] {
        guard let interval = calendar.dateInterval(of: .month, for: visibleMonth),
              let range = calendar.range(of: .day, in: .month, for: visibleMonth) else {
            return []
        }

        let firstWeekday = calendar.component(.weekday, from: interval.start)
        let leadingBlanks = (firstWeekday - calendar.firstWeekday + 7) % 7

        let dates: [Date?] = range.compactMap { day in
            calendar.date(byAdding: .day, value: day - 1, to: interval.start)
        }
        return Array(repeating: nil, count: leadingBlanks) + dates
    }

    private func shiftMonth(by months: Int) {
        guard let shifted = calendar.date(byAdding: .month, value: months, to: visibleMonth) else { return }
        visibleMonth = shifted
    }
}

/// One day. A look turns the cell into its own thumbnail.
struct DayCell: View {
    let day: Date
    let outfit: Outfit?
    let isToday: Bool
    var onSelect: (Outfit) -> Void

    private let calendar = Localization.calendar

    var body: some View {
        Button {
            if let outfit { onSelect(outfit) }
        } label: {
            ZStack {
                if let outfit {
                    AssetImage(ref: outfit.cutout)
                        .frame(height: 58)
                } else {
                    Text("\(calendar.component(.day, from: day))")
                        .font(.system(size: 12, weight: isToday ? .semibold : .regular))
                        .foregroundStyle(isToday ? Theme.Palette.ink : Theme.Palette.inkTertiary)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 62)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(isToday ? Theme.Palette.ground : .clear)
            )
        }
        .buttonStyle(.plain)
        .disabled(outfit == nil)
        .accessibilityLabel(accessibilityLabel)
    }

    private var accessibilityLabel: String {
        let number = calendar.component(.day, from: day)
        return outfit == nil ? "\(number) 日，没有穿搭" : "\(number) 日，打开这套穿搭"
    }
}
