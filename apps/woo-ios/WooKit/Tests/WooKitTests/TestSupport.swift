import Foundation
@testable import WooKit

/// Collects progress values from whatever executor the service reports on, so
/// tests can assert on the sequence afterwards. A plain `var` cannot be
/// captured by a `@Sendable` progress handler, hence the small class.
final class ProgressRecorder: @unchecked Sendable {
    private let lock = NSLock()
    private var values: [Double] = []

    var handler: ProgressHandler {
        { [weak self] value in
            guard let self else { return }
            self.lock.lock()
            self.values.append(value)
            self.lock.unlock()
        }
    }

    var recorded: [Double] {
        lock.lock()
        defer { lock.unlock() }
        return values
    }
}
