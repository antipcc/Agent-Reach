import XCTest
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
@testable import WooKit

/// Answers a scripted sequence and records what it was asked, so a
/// four-call flow can be asserted without an account or a network.
private final class ScriptedTransport: HTTPTransport, @unchecked Sendable {
    struct Call {
        let method: String
        let path: String
        let body: Data?
        let authorization: String?

        /// The JSON body, for asserting on what was actually sent.
        var json: [String: Any] {
            guard let body,
                  let object = try? JSONSerialization.jsonObject(with: body) as? [String: Any]
            else { return [:] }
            return object
        }
    }

    private let lock = NSLock()
    private var responses: [(Data, Int)]
    private var recorded: [Call] = []

    init(responses: [(Data, Int)]) {
        self.responses = responses
    }

    convenience init(json: [String]) {
        self.init(responses: json.map { (Data($0.utf8), 200) })
    }

    var calls: [Call] {
        lock.lock(); defer { lock.unlock() }
        return recorded
    }

    func send(_ request: URLRequest) async throws -> (Data, Int) {
        lock.lock()
        recorded.append(Call(
            method: request.httpMethod ?? "",
            path: request.url?.path ?? "",
            body: request.httpBody,
            authorization: request.value(forHTTPHeaderField: "Authorization")
        ))
        let next = responses.isEmpty ? (Data("{}".utf8), 500) : responses.removeFirst()
        lock.unlock()
        return next
    }
}

final class TripoModelServiceTests: XCTestCase {
    private let photo = ImageData.jpeg(Data([0xFF, 0xD8, 0xFF, 0xE0, 0x55, 0x66]))

    /// Upload, create, poll to success, convert, poll to success, download.
    private func happyPath() -> ScriptedTransport {
        ScriptedTransport(responses: [
            (Data(#"{"code":0,"data":{"image_token":"tok-1"}}"#.utf8), 200),
            (Data(#"{"code":0,"data":{"task_id":"model-1"}}"#.utf8), 200),
            (Data(#"{"code":0,"data":{"status":"running","progress":40}}"#.utf8), 200),
            (Data(#"{"code":0,"data":{"status":"success","progress":100,"output":{"pbr_model":"https://cdn.example/m.glb"}}}"#.utf8), 200),
            (Data(#"{"code":0,"data":{"task_id":"convert-1"}}"#.utf8), 200),
            (Data(#"{"code":0,"data":{"status":"success","output":{"model":"https://cdn.example/m.usdz"}}}"#.utf8), 200),
            (Data("USDZBYTES".utf8), 200)
        ])
    }

    private func makeService(_ transport: ScriptedTransport) -> TripoModelService {
        TripoModelService(apiKey: "secret", pollInterval: 0, timeout: 30, transport: transport)
    }

    func testItUploadsCreatesPollsConvertsAndDownloads() async throws {
        let transport = happyPath()
        let recorder = ProgressRecorder()

        let result = try await makeService(transport).generateModel(
            from: photo,
            progress: recorder.handler
        )

        XCTAssertEqual(String(decoding: result.data, as: UTF8.self), "USDZBYTES")
        XCTAssertEqual(result.format, .usdz, "the card can only render what Model I/O opens")
        XCTAssertFalse(result.isPlaceholder)

        let calls = transport.calls
        XCTAssertEqual(calls.count, 7)
        XCTAssertEqual(calls.map(\.method), ["POST", "POST", "GET", "GET", "POST", "GET", "GET"])
        XCTAssertTrue(calls[0].path.hasSuffix("/upload"))
        XCTAssertTrue(calls[1].path.hasSuffix("/task"))
        XCTAssertTrue(calls[2].path.hasSuffix("/task/model-1"))
        XCTAssertTrue(calls[4].path.hasSuffix("/task"))
        XCTAssertTrue(calls[5].path.hasSuffix("/task/convert-1"))
    }

    func testTheModelTaskCarriesTheUploadedTokenAndTheModelVersion() async throws {
        let transport = happyPath()
        _ = try await makeService(transport).generateModel(from: photo, progress: { _ in })

        let create = transport.calls[1].json
        XCTAssertEqual(create["type"] as? String, "image_to_model")
        XCTAssertEqual(create["model_version"] as? String, TripoModelService.defaultModelVersion)

        let file = create["file"] as? [String: Any]
        XCTAssertEqual(file?["file_token"] as? String, "tok-1", "the task must reference the upload")
        XCTAssertEqual(file?["type"] as? String, "jpg")
    }

    func testTheConversionAsksForUSDZAgainstTheFinishedModelTask() async throws {
        let transport = happyPath()
        _ = try await makeService(transport).generateModel(from: photo, progress: { _ in })

        let convert = transport.calls[4].json
        XCTAssertEqual(convert["type"] as? String, "convert_model")
        XCTAssertEqual(convert["original_model_task_id"] as? String, "model-1")
        XCTAssertEqual(convert["format"] as? String, "USDZ", "GLB would not open on iOS")
    }

    func testEveryAPICallIsAuthorizedAndTheDownloadIsNot() async throws {
        let transport = happyPath()
        _ = try await makeService(transport).generateModel(from: photo, progress: { _ in })

        for call in transport.calls.prefix(6) {
            XCTAssertEqual(call.authorization, "Bearer secret", "\(call.path) went out unsigned")
        }
        // The download URL is pre-signed by the CDN; sending the key there
        // would leak it to a third-party host.
        XCTAssertNil(transport.calls[6].authorization)
    }

    func testProgressClimbsThroughBothTasksAndEndsAtOne() async throws {
        let transport = happyPath()
        let recorder = ProgressRecorder()
        _ = try await makeService(transport).generateModel(from: photo, progress: recorder.handler)

        let values = recorder.recorded
        XCTAssertEqual(values, values.sorted(), "progress must never go backwards")
        XCTAssertEqual(values.last, 1)
        XCTAssertTrue(
            values.contains { $0 > 0.05 && $0 < 0.75 },
            "the model task owns the middle of the bar"
        )
    }

    func testANonZeroCodeIsAFailureEvenOnHTTP200() async {
        let transport = ScriptedTransport(responses: [
            (Data(#"{"code":2000,"message":"insufficient balance"}"#.utf8), 200)
        ])
        await assertFails(makeService(transport), containing: "insufficient balance")
    }

    func testAFailedTaskReportsTheServiceReason() async {
        let transport = ScriptedTransport(responses: [
            (Data(#"{"code":0,"data":{"image_token":"tok-1"}}"#.utf8), 200),
            (Data(#"{"code":0,"data":{"task_id":"model-1"}}"#.utf8), 200),
            (Data(#"{"code":0,"data":{"status":"failed","error_msg":"no subject found"}}"#.utf8), 200)
        ])
        await assertFails(makeService(transport), containing: "no subject found")
    }

    func testAnEmptyDownloadIsNotPassedOffAsAModel() async {
        let transport = ScriptedTransport(responses: [
            (Data(#"{"code":0,"data":{"image_token":"t"}}"#.utf8), 200),
            (Data(#"{"code":0,"data":{"task_id":"m"}}"#.utf8), 200),
            (Data(#"{"code":0,"data":{"status":"success","output":{"model":"https://cdn.example/m.glb"}}}"#.utf8), 200),
            (Data(#"{"code":0,"data":{"task_id":"c"}}"#.utf8), 200),
            (Data(#"{"code":0,"data":{"status":"success","output":{"model":"https://cdn.example/m.usdz"}}}"#.utf8), 200),
            (Data(), 200)
        ])
        await assertFails(makeService(transport), containing: "下载失败")
    }

    func testATripoKeyAloneTakesOverReconstruction() {
        let provider = AIProvider.live(config: AIConfig(tripoAPIKey: "k"))
        XCTAssertTrue(provider.modelGeneration is TripoModelService)
        XCTAssertTrue(provider.tryOn is MockTryOnService, "nothing else was configured")
    }

    func testAnEmptyTripoKeyIsNotConfiguration() {
        XCTAssertFalse(AIConfig(tripoAPIKey: "").isTripoConfigured)
        XCTAssertFalse(AIConfig.empty.isTripoConfigured)
        XCTAssertTrue(AIConfig(tripoAPIKey: "k").isTripoConfigured)
    }

    private func assertFails(
        _ service: TripoModelService,
        containing fragment: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) async {
        do {
            _ = try await service.generateModel(from: photo, progress: { _ in })
            XCTFail("Expected a failure", file: file, line: line)
        } catch let error as WooError {
            let described = error.errorDescription ?? ""
            XCTAssertTrue(
                described.contains(fragment),
                "\(described) should mention \(fragment)",
                file: file, line: line
            )
        } catch {
            XCTFail("Unexpected error \(error)", file: file, line: line)
        }
    }
}
