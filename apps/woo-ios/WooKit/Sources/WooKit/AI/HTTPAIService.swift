import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// One HTTP client implementing all four AI protocols.
///
/// The wire contract below is a placeholder that matches how most hosted
/// image models work — multipart upload in, JSON with base64 images out:
///
/// ```
/// POST {baseURL}{path}          Authorization: Bearer {apiKey}
/// multipart/form-data: image=<bytes> [, garment_0..n=<bytes>]
/// → 200 {"images": ["<base64>", …], "items": [{"name","category"}]}
/// ```
///
/// TODO: replace `decodeImages` / `decodeGarments` with the vendor's real
/// response shape once one is chosen. Nothing outside this file needs to change.
///
/// `@unchecked Sendable`: `URLSession` is a class, so no annotation will make
/// it a value type — but it is documented thread-safe, and every service
/// protocol here requires `Sendable`.
public struct HTTPAIService: BackgroundRemovalService, GarmentExtractionService, TryOnService,
                             ModelGenerationService, SpinService, @unchecked Sendable {
    let config: AIConfig
    let session: URLSession

    public init(config: AIConfig, session: URLSession = .shared) {
        self.config = config
        self.session = session
    }

    // MARK: - Services

    public func removeBackground(from image: ImageData) async throws -> ImageData {
        let path = try requirePath(config.backgroundRemovalPath, name: "抠图")
        let data = try await post(path: path, parts: [MultipartPart(name: "image", image: image)])
        guard let first = try decodeImages(data).first else {
            throw WooError.aiFailed("抠图服务没有返回图片。")
        }
        return first
    }

    public func extractGarments(from image: ImageData) async throws -> [ExtractedGarment] {
        let path = try requirePath(config.garmentExtractionPath, name: "单品拆解")
        let data = try await post(path: path, parts: [MultipartPart(name: "image", image: image)])
        return try decodeGarments(data)
    }

    public func tryOn(
        person: ImageData,
        garments: [ImageData],
        progress: @escaping ProgressHandler
    ) async throws -> ImageData {
        let path = try requirePath(config.tryOnPath, name: "换装")
        progress(0.05)
        var parts = [MultipartPart(name: "person", image: person)]
        for (index, garment) in garments.enumerated() {
            parts.append(MultipartPart(name: "garment_\(index)", image: garment))
        }
        // A single request gives no intermediate progress; report the two
        // moments we actually know about rather than faking a smooth bar.
        let data = try await post(path: path, parts: parts)
        progress(1)
        guard let first = try decodeImages(data).first else {
            throw WooError.aiFailed("换装服务没有返回图片。")
        }
        return first
    }

    /// Submit, poll, download. Reconstruction takes tens of seconds, so every
    /// provider worth using hands back a job id rather than a mesh; a provider
    /// that answers with the mesh straight away is handled too.
    public func generateModel(
        from image: ImageData,
        progress: @escaping ProgressHandler
    ) async throws -> Model3DResult {
        let path = try requirePath(config.modelPath, name: "3D 重建")
        progress(0.02)

        let submitted = try decode(
            try await post(path: path, parts: [MultipartPart(name: "image", image: image)])
        )

        // Some providers answer synchronously. Take the mesh if it is there.
        if let ready = try await downloadModel(from: submitted) {
            progress(1)
            return ready
        }

        guard let jobID = submitted.jobID ?? submitted.id else {
            throw WooError.aiFailed("重建服务既没返回模型，也没返回任务 ID。")
        }

        let started = Date()
        let deadline = started.addingTimeInterval(config.modelTimeout)
        while Date() < deadline {
            try await Task.sleep(for: .seconds(config.modelPollInterval))
            try Task.checkCancellation()

            let poll = try decode(try await get(path: "\(path)/\(jobID)"))

            switch poll.status?.lowercased() {
            case "failed", "error", "cancelled":
                throw WooError.aiFailed(poll.error ?? "重建失败。")
            case "succeeded", "success", "done", "completed":
                guard let finished = try await downloadModel(from: poll) else {
                    throw WooError.aiFailed("重建完成了，但没有拿到模型。")
                }
                progress(1)
                return finished
            default:
                // Providers that report progress get to drive the bar. For the
                // rest, creep toward 0.9 on elapsed time so the screen never
                // looks stuck at zero — and never claims to be done.
                let elapsed = Date().timeIntervalSince(started) / config.modelTimeout
                progress(min(0.9, poll.progress ?? (0.02 + elapsed * 0.88)))
            }
        }

        throw WooError.aiFailed("重建超时，已等待 \(Int(config.modelTimeout)) 秒。")
    }

    /// Pulls the mesh out of a response, whichever way it was handed over.
    /// Returns nil when the response is only a job receipt.
    private func downloadModel(from envelope: Envelope) async throws -> Model3DResult? {
        let rawFormat = envelope.format ?? "usdz"
        guard let format = Model3DAsset.Format.loadable(rawFormat) else {
            throw WooError.aiFailed(
                "服务返回的是 \(rawFormat) 模型，iOS 打不开。请让它返回 usdz。"
            )
        }

        if let encoded = envelope.model, let bytes = Data(base64Encoded: encoded), !bytes.isEmpty {
            return Model3DResult(data: bytes, format: format)
        }

        guard let link = envelope.modelURL, let url = URL(string: link) else { return nil }
        var request = URLRequest(url: url)
        request.timeoutInterval = config.timeout
        let bytes = try await send(request)
        guard !bytes.isEmpty else {
            throw WooError.aiFailed("下载到的模型是空的。")
        }
        return Model3DResult(data: bytes, format: format)
    }

    public func generateSpin(
        from image: ImageData,
        frameCount: Int,
        progress: @escaping ProgressHandler
    ) async throws -> SpinResult {
        let path = try requirePath(config.spinPath, name: "360°")
        progress(0.05)
        let parts = [
            MultipartPart(name: "image", image: image),
            MultipartPart(name: "frame_count", text: String(frameCount))
        ]
        let data = try await post(path: path, parts: parts)
        progress(1)
        let frames = try decodeImages(data)
        guard frames.count > 1 else {
            throw WooError.aiFailed("360° 服务返回的帧数太少。")
        }
        return SpinResult(frames: frames)
    }

    // MARK: - Transport

    private func requirePath(_ path: String?, name: String) throws -> String {
        guard let path, config.baseURL != nil else {
            throw WooError.aiUnavailable("还没有配置\(name)的服务地址。")
        }
        return path
    }

    private func post(path: String, parts: [MultipartPart]) async throws -> Data {
        guard let baseURL = config.baseURL else {
            throw WooError.aiUnavailable("还没有配置 AI 服务地址。")
        }
        let url = baseURL.appendingPathComponent(path)
        let boundary = "woo-\(UUID().uuidString)"

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = config.timeout
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        if let apiKey = config.apiKey {
            request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        }
        request.httpBody = MultipartPart.body(parts, boundary: boundary)

        var attempt = 0
        while true {
            do {
                return try await send(request)
            } catch {
                attempt += 1
                if attempt > config.maxRetries || !isRetryable(error) { throw error }
                // 1s, 2s, 4s — enough to ride out a cold model container.
                try await Task.sleep(for: .seconds(pow(2.0, Double(attempt - 1))))
            }
        }
    }

    private func get(path: String) async throws -> Data {
        guard let baseURL = config.baseURL else {
            throw WooError.aiUnavailable("还没有配置 AI 服务地址。")
        }
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "GET"
        request.timeoutInterval = config.timeout
        if let apiKey = config.apiKey {
            request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        }
        return try await send(request)
    }

    /// Continuation over `dataTask` rather than the async API: the same code
    /// then compiles on Linux, where WooKit's tests run.
    private func send(_ request: URLRequest) async throws -> Data {
        try await withCheckedThrowingContinuation { continuation in
            let task = session.dataTask(with: request) { data, response, error in
                if let error {
                    continuation.resume(throwing: WooError.aiFailed(error.localizedDescription))
                    return
                }
                guard let http = response as? HTTPURLResponse else {
                    continuation.resume(throwing: WooError.aiFailed("AI 服务没有响应。"))
                    return
                }
                guard (200..<300).contains(http.statusCode) else {
                    let detail = data.flatMap { String(data: $0, encoding: .utf8) } ?? ""
                    continuation.resume(
                        throwing: WooError.aiFailed("AI 服务出错（\(http.statusCode)）。\(detail.prefix(200))")
                    )
                    return
                }
                continuation.resume(returning: data ?? Data())
            }
            task.resume()
        }
    }

    private func isRetryable(_ error: Error) -> Bool {
        guard case let WooError.aiFailed(detail) = error else { return false }
        // Server-side and transport hiccups are worth another go; a 4xx is not.
        return detail.contains("(5") || detail.contains("timed out") || detail.contains("network")
    }

    // MARK: - Response decoding (vendor-specific — replace as needed)

    private struct Envelope: Decodable {
        struct Item: Decodable {
            let name: String?
            let category: String?
            let image: String?
        }
        let images: [String]?
        let image: String?
        let items: [Item]?

        // Reconstruction jobs
        let id: String?
        let jobID: String?
        let status: String?
        let progress: Double?
        let error: String?
        let model: String?
        let modelURL: String?
        let format: String?

        enum CodingKeys: String, CodingKey {
            case images, image, items, id, status, progress, error, model, format
            case jobID = "job_id"
            case modelURL = "model_url"
        }
    }

    private func decodeImages(_ data: Data) throws -> [ImageData] {
        let envelope = try decode(data)
        let encoded = envelope.images ?? envelope.image.map { [$0] } ?? []
        return try encoded.map { try decodeBase64Image($0) }
    }

    private func decodeGarments(_ data: Data) throws -> [ExtractedGarment] {
        let envelope = try decode(data)
        guard let items = envelope.items else { return [] }
        return try items.compactMap { item in
            guard let encoded = item.image else { return nil }
            return ExtractedGarment(
                name: item.name ?? "单品",
                category: item.category.flatMap(GarmentCategory.init(rawValue:)) ?? .tops,
                cutout: try decodeBase64Image(encoded)
            )
        }
    }

    private func decode(_ data: Data) throws -> Envelope {
        do {
            return try JSONDecoder().decode(Envelope.self, from: data)
        } catch {
            throw WooError.aiFailed("读不懂 AI 服务的响应。")
        }
    }

    private func decodeBase64Image(_ encoded: String) throws -> ImageData {
        // Tolerate `data:image/png;base64,…` as well as a bare payload.
        let payload = encoded.contains(",") ? String(encoded.split(separator: ",").last ?? "") : encoded
        guard let bytes = Data(base64Encoded: payload), !bytes.isEmpty else {
            throw WooError.aiFailed("AI 服务返回了一张读不出的图片。")
        }
        return ImageData(data: bytes, format: .png)
    }
}

/// One field of a multipart body — a file or a plain value.
struct MultipartPart {
    let name: String
    let filename: String?
    let contentType: String?
    let content: Data

    init(name: String, image: ImageData) {
        self.name = name
        self.filename = "\(name).\(image.format.fileExtension)"
        self.contentType = image.format.mimeType
        self.content = image.data
    }

    init(name: String, text: String) {
        self.name = name
        self.filename = nil
        self.contentType = nil
        self.content = Data(text.utf8)
    }

    static func body(_ parts: [MultipartPart], boundary: String) -> Data {
        var body = Data()
        for part in parts {
            body.append(Data("--\(boundary)\r\n".utf8))
            var disposition = "Content-Disposition: form-data; name=\"\(part.name)\""
            if let filename = part.filename {
                disposition += "; filename=\"\(filename)\""
            }
            body.append(Data("\(disposition)\r\n".utf8))
            if let contentType = part.contentType {
                body.append(Data("Content-Type: \(contentType)\r\n".utf8))
            }
            body.append(Data("\r\n".utf8))
            body.append(part.content)
            body.append(Data("\r\n".utf8))
        }
        body.append(Data("--\(boundary)--\r\n".utf8))
        return body
    }
}
