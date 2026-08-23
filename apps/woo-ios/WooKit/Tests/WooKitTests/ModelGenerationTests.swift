import XCTest
@testable import WooKit

/// A reconstruction service that is simply not configured — the state the app
/// is in until someone supplies endpoints.
private struct UnavailableModelService: ModelGenerationService {
    func generateModel(
        from image: ImageData,
        progress: @escaping ProgressHandler
    ) async throws -> Model3DResult {
        throw WooError.aiUnavailable("No 3D reconstruction endpoint is configured yet.")
    }
}

final class ModelGenerationTests: XCTestCase {
    private let photo = ImageData.jpeg(Data([0xFF, 0xD8, 0xFF, 0xE0, 0x33, 0x44]))

    private func makeService(model: (any ModelGenerationService)? = nil) -> LibraryService {
        var provider = AIProvider.mock(latency: .instant)
        if let model { provider.modelGeneration = model }
        return LibraryService(store: InMemoryOutfitStore(), provider: provider)
    }

    // MARK: - The placeholder mesh

    func testThePlaceholderMannequinIsWellFormedOBJ() throws {
        let text = PlaceholderModelBuilder.mannequinOBJ()
        let lines = text.split(separator: "\n").map(String.init)

        let vertices = lines.filter { $0.hasPrefix("v ") }
        let faces = lines.filter { $0.hasPrefix("f ") }
        XCTAssertFalse(vertices.isEmpty)
        XCTAssertFalse(faces.isEmpty)

        // Eleven boxes, eight vertices and six quads each.
        XCTAssertEqual(vertices.count, 11 * 8)
        XCTAssertEqual(faces.count, 11 * 6)

        for vertex in vertices {
            let numbers = vertex.dropFirst(2).split(separator: " ")
            XCTAssertEqual(numbers.count, 3, "every vertex needs three coordinates")
            XCTAssertTrue(numbers.allSatisfy { Double($0) != nil }, "coordinates must parse: \(vertex)")
        }

        // OBJ indices are 1-based and global; an out-of-range one loads as an
        // empty or corrupt mesh rather than failing loudly.
        for face in faces {
            let indices = face.dropFirst(2).split(separator: " ").compactMap { Int($0) }
            XCTAssertEqual(indices.count, 4, "every face is a quad: \(face)")
            XCTAssertTrue(
                indices.allSatisfy { $0 >= 1 && $0 <= vertices.count },
                "face index out of range: \(face)"
            )
        }
    }

    func testThePlaceholderStandsOnTheGroundAndFacesForward() throws {
        let vertices = PlaceholderModelBuilder.mannequinOBJ()
            .split(separator: "\n")
            .filter { $0.hasPrefix("v ") }
            .map { $0.dropFirst(2).split(separator: " ").compactMap { Double($0) } }

        let ys = vertices.map { $0[1] }
        let zs = vertices.map { $0[2] }
        XCTAssertEqual(ys.min() ?? -1, 0, accuracy: 0.001, "feet should rest on y = 0")
        XCTAssertGreaterThan(ys.max() ?? 0, 1.5, "roughly human height")
        // The nose pokes further forward than the head block it sits on.
        XCTAssertGreaterThan(zs.max() ?? 0, 0.11, "there must be a front to tell from the back")
    }

    // MARK: - Generating

    func testGeneratingAModelAttachesItAndMarksItAStandIn() async throws {
        let service = makeService()
        let outfit = try await service.ingestPhoto(photo)

        let recorder = ProgressRecorder()
        let updated = try await service.generateModel(for: outfit.id, progress: recorder.handler)

        XCTAssertTrue(updated.hasModel)
        XCTAssertEqual(updated.model?.format, .obj)
        XCTAssertTrue(updated.model?.isPlaceholder == true, "the mock must not pass as a reconstruction")
        XCTAssertEqual(recorder.recorded.last, 1)

        let stored = try await service.store.readAsset(try XCTUnwrap(updated.model?.file))
        XCTAssertTrue(String(decoding: stored, as: UTF8.self).contains("v "))
    }

    func testRegeneratingAModelDropsTheFileItReplaced() async throws {
        let service = makeService()
        let outfit = try await service.ingestPhoto(photo)
        let first = try await service.generateModel(for: outfit.id)
        let stale = try XCTUnwrap(first.model?.file)

        let second = try await service.generateModel(for: outfit.id)
        XCTAssertNotEqual(second.model?.file, stale)

        do {
            _ = try await service.store.readAsset(stale)
            XCTFail("The superseded mesh should have been cleaned up")
        } catch let error as WooError {
            XCTAssertEqual(error, .assetNotFound(stale.filename))
        }
    }

    func testTheModelFileIsDeletedWithTheLook() async throws {
        let service = makeService()
        let outfit = try await service.ingestPhoto(photo)
        let withModel = try await service.generateModel(for: outfit.id)
        let file = try XCTUnwrap(withModel.model?.file)
        XCTAssertTrue(withModel.ownedAssets.contains(file), "the look owns its mesh")

        try await service.deleteOutfit(id: outfit.id)
        do {
            _ = try await service.store.readAsset(file)
            XCTFail("Deleting the look should take its mesh with it")
        } catch let error as WooError {
            XCTAssertEqual(error, .assetNotFound(file.filename))
        }
    }

    // MARK: - Falling back

    func testTurnaroundFallsBackToFramesWhenReconstructionIsNotConfigured() async throws {
        let service = makeService(model: UnavailableModelService())
        let outfit = try await service.ingestPhoto(photo)

        let updated = try await service.generateTurnaround(for: outfit.id)

        XCTAssertFalse(updated.hasModel, "there was no reconstruction service to call")
        XCTAssertTrue(updated.hasSpin, "so the frame ring stands in for it")
        XCTAssertTrue(updated.isTurnable)
    }

    func testTurnaroundPrefersAMeshWhenOneCanBeMade() async throws {
        let service = makeService()
        let outfit = try await service.ingestPhoto(photo)

        let updated = try await service.generateTurnaround(for: outfit.id)

        XCTAssertTrue(updated.hasModel)
        XCTAssertFalse(updated.hasSpin, "no need to render frames as well")
    }

    // MARK: - Wiring

    func testReconstructionOnlyGoesOverTheWireWhenAnEndpointIsConfigured() {
        let unconfigured = AIProvider.live(config: .empty)
        XCTAssertTrue(unconfigured.modelGeneration is MockModelGenerationService)

        let configured = AIProvider.live(config: AIConfig(
            baseURL: URL(string: "https://example.invalid"),
            apiKey: "k",
            modelPath: "/reconstruct"
        ))
        XCTAssertTrue(configured.modelGeneration is HTTPAIService)
        XCTAssertTrue(configured.spin is MockSpinService, "frames were not configured")
    }

    func testAModelAssetSurvivesACodingRoundTrip() throws {
        let outfit = Outfit(
            date: Date(timeIntervalSince1970: 1_787_000_000),
            cutout: AssetRef(filename: "cutout.png"),
            model: Model3DAsset(
                file: AssetRef(filename: "model-a.usdz"),
                format: .usdz,
                isPlaceholder: false,
                createdAt: Date(timeIntervalSince1970: 1_787_000_000)
            )
        )

        let data = try LibraryCoding.encoder.encode(outfit)
        let decoded = try LibraryCoding.decoder.decode(Outfit.self, from: data)
        XCTAssertEqual(decoded, outfit)
        XCTAssertEqual(decoded.model?.format, .usdz)
    }

    /// The library stores dates as readable ISO 8601 with fractional seconds,
    /// which is millisecond-precise — not bit-exact. Comparing a freshly made
    /// `Outfit` with its reloaded self will therefore differ below a
    /// millisecond, and that is the contract, not a bug.
    func testStoredDatesAreMillisecondPrecise() throws {
        let now = Date()
        let outfit = Outfit(date: now, cutout: AssetRef(filename: "cutout.png"))

        let data = try LibraryCoding.encoder.encode(outfit)
        let decoded = try LibraryCoding.decoder.decode(Outfit.self, from: data)

        XCTAssertEqual(
            decoded.date.timeIntervalSinceReferenceDate,
            now.timeIntervalSinceReferenceDate,
            accuracy: 0.001,
            "fractional seconds must survive — plain ISO 8601 would lose up to a full second"
        )
        XCTAssertTrue(
            String(decoding: data, as: UTF8.self).contains("."),
            "the stored timestamp should carry a fractional part"
        )
    }

    func testGLBIsRejectedByNameSoTheFailureIsActionable() {
        XCTAssertNil(Model3DAsset.Format.loadable("glb"), "iOS cannot open glTF binaries")
        XCTAssertNil(Model3DAsset.Format.loadable("gltf"))
        XCTAssertEqual(Model3DAsset.Format.loadable("USDZ"), .usdz)
        XCTAssertEqual(Model3DAsset.Format.loadable(" obj "), .obj)
    }
}
