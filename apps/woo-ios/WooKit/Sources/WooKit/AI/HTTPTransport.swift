import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// One request in, bytes and a status out. Everything that talks to a vendor
/// goes through this, which is what makes a multi-step flow assertable in a
/// test rather than only observable against a live account.
public protocol HTTPTransport: Sendable {
    func send(_ request: URLRequest) async throws -> (Data, Int)
}

/// The shipping transport.
///
/// Built on `dataTask` with a continuation rather than the async API, so the
/// same code compiles on Linux, where WooKit's tests run.
public struct URLSessionTransport: HTTPTransport, @unchecked Sendable {
    let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    public func send(_ request: URLRequest) async throws -> (Data, Int) {
        try await withCheckedThrowingContinuation { continuation in
            let task = session.dataTask(with: request) { data, response, error in
                if let error {
                    continuation.resume(throwing: WooError.aiFailed(error.localizedDescription))
                    return
                }
                guard let http = response as? HTTPURLResponse else {
                    continuation.resume(throwing: WooError.aiFailed("服务没有响应。"))
                    return
                }
                continuation.resume(returning: (data ?? Data(), http.statusCode))
            }
            task.resume()
        }
    }
}
