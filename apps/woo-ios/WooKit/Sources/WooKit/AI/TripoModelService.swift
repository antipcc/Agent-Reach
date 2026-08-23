import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// Real single-image reconstruction, against Tripo3D's open API.
///
/// Four calls, not the three a naive client would guess, because the model
/// task produces GLB and Model I/O cannot open glTF on iOS — a second
/// `convert_model` task is what turns it into something the home card can
/// actually render:
///
/// 1. `POST /upload`      multipart `file`      → `data.image_token`
/// 2. `POST /task`        `image_to_model`      → `data.task_id`
/// 3. `GET  /task/{id}`   until `status` settles
/// 4. `POST /task`        `convert_model`, `format: USDZ`, poll, download
///
/// Shapes taken from Tripo's own Python client (`tripo3d` on PyPI) rather than
/// from documentation, so they match what the service actually accepts.
///
/// `@unchecked Sendable`: every field is a value type; `URL` is one too, but
/// swift-corelibs-foundation has not annotated it.
public struct TripoModelService: ModelGenerationService, @unchecked Sendable {
    public static let defaultBaseURL = URL(string: "https://api.tripo3d.ai/v2/openapi")!
    /// The version Tripo's own client defaults to.
    public static let defaultModelVersion = "v2.5-20250123"

    let apiKey: String
    let baseURL: URL
    let modelVersion: String
    let pollInterval: TimeInterval
    let timeout: TimeInterval
    let transport: any HTTPTransport

    public init(
        apiKey: String,
        baseURL: URL = TripoModelService.defaultBaseURL,
        modelVersion: String = TripoModelService.defaultModelVersion,
        pollInterval: TimeInterval = 3,
        timeout: TimeInterval = 600,
        transport: any HTTPTransport = URLSessionTransport()
    ) {
        self.apiKey = apiKey
        self.baseURL = baseURL
        self.modelVersion = modelVersion
        self.pollInterval = pollInterval
        self.timeout = timeout
        self.transport = transport
    }

    public func generateModel(
        from image: ImageData,
        progress: @escaping ProgressHandler
    ) async throws -> Model3DResult {
        guard !image.isEmpty else { throw WooError.aiFailed("没有可用的照片。") }
        let started = Date()

        progress(0.02)
        let imageToken = try await upload(image)

        progress(0.05)
        let modelTask = try await createTask([
            "type": "image_to_model",
            "file": ["type": image.format == .png ? "png" : "jpg", "file_token": imageToken],
            "model_version": modelVersion
        ])

        // The bulk of the wait is here, so it owns the bulk of the bar.
        try await awaitTask(modelTask, started: started, from: 0.05, to: 0.75, progress: progress)

        let convertTask = try await createTask([
            "type": "convert_model",
            "original_model_task_id": modelTask,
            "format": "USDZ"
        ])
        let converted = try await awaitTask(
            convertTask, started: started, from: 0.75, to: 0.95, progress: progress
        )

        guard let link = converted.modelURL, let url = URL(string: link) else {
            throw WooError.aiFailed("转换完成了，但没有拿到可下载的模型。")
        }
        let bytes = try await download(url)
        progress(1)
        return Model3DResult(data: bytes, format: .usdz, isPlaceholder: false)
    }

    // MARK: - Steps

    private func upload(_ image: ImageData) async throws -> String {
        let boundary = "woo-\(UUID().uuidString)"
        var request = signed("/upload", method: "POST")
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        request.httpBody = MultipartPart.body(
            [MultipartPart(name: "file", image: image)],
            boundary: boundary
        )

        let envelope = try await perform(request)
        // The upload endpoint names its token differently from every other
        // endpoint; accept both rather than break on a rename.
        guard let token = envelope.imageToken ?? envelope.fileToken else {
            throw WooError.aiFailed("上传成功了，但没有拿到图片令牌。")
        }
        return token
    }

    private func createTask(_ body: [String: Any]) async throws -> String {
        var request = signed("/task", method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let envelope = try await perform(request)
        guard let taskID = envelope.taskID else {
            throw WooError.aiFailed("没有拿到任务 ID。")
        }
        return taskID
    }

    /// Polls one task to a terminal state, reporting progress into the slice
    /// of the bar it owns.
    @discardableResult
    private func awaitTask(
        _ taskID: String,
        started: Date,
        from: Double,
        to: Double,
        progress: @escaping ProgressHandler
    ) async throws -> TripoData {
        while Date().timeIntervalSince(started) < timeout {
            let data = try await perform(signed("/task/\(taskID)", method: "GET"))

            switch data.status?.lowercased() {
            case "success":
                progress(to)
                return data
            case "failed", "cancelled", "banned", "expired":
                throw WooError.aiFailed(data.errorMessage ?? "重建失败（\(data.status ?? "未知")）。")
            default:
                // Tripo reports 0–100; map it into this step's slice.
                let fraction = min(max((data.progress ?? 0) / 100, 0), 1)
                progress(from + (to - from) * fraction)
            }

            try await Task.sleep(for: .seconds(pollInterval))
            try Task.checkCancellation()
        }
        throw WooError.aiFailed("重建超时，已等待 \(Int(timeout)) 秒。")
    }

    private func download(_ url: URL) async throws -> Data {
        var request = URLRequest(url: url)
        request.timeoutInterval = 120
        let (bytes, status) = try await transport.send(request)
        guard (200..<300).contains(status), !bytes.isEmpty else {
            throw WooError.aiFailed("模型下载失败（\(status)）。")
        }
        return bytes
    }

    // MARK: - Plumbing

    private func signed(_ path: String, method: String) -> URLRequest {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.timeoutInterval = 120
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        return request
    }

    /// Tripo wraps everything in `{"code": 0, "data": {…}}`, and a non-zero
    /// code arrives with HTTP 200, so the status alone never tells the story.
    private func perform(_ request: URLRequest) async throws -> TripoData {
        let (bytes, status) = try await transport.send(request)
        guard (200..<300).contains(status) else {
            throw WooError.aiFailed("Tripo 请求失败（\(status)）。")
        }
        let envelope: TripoEnvelope
        do {
            envelope = try JSONDecoder().decode(TripoEnvelope.self, from: bytes)
        } catch {
            throw WooError.aiFailed("读不懂 Tripo 的响应。")
        }
        guard envelope.code == 0 else {
            throw WooError.aiFailed(envelope.message ?? "Tripo 返回错误码 \(envelope.code)。")
        }
        guard let data = envelope.data else {
            throw WooError.aiFailed("Tripo 的响应里没有数据。")
        }
        return data
    }
}

struct TripoEnvelope: Decodable {
    let code: Int
    let message: String?
    let data: TripoData?
}

struct TripoData: Decodable {
    let imageToken: String?
    let fileToken: String?
    let taskID: String?
    let status: String?
    let progress: Double?
    let errorMessage: String?
    let output: Output?

    struct Output: Decodable {
        let model: String?
        let pbrModel: String?

        enum CodingKeys: String, CodingKey {
            case model
            case pbrModel = "pbr_model"
        }
    }

    /// Prefer the textured mesh; fall back to the plain one.
    var modelURL: String? { output?.pbrModel ?? output?.model }

    enum CodingKeys: String, CodingKey {
        case status, progress, output
        case imageToken = "image_token"
        case fileToken = "file_token"
        case taskID = "task_id"
        case errorMessage = "error_msg"
    }
}
