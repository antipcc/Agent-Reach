import Foundation

/// The shipping store: image bytes as loose files, metadata as one JSON
/// document. An actor so concurrent writes from capture, try-on and spin
/// jobs can't interleave and lose each other.
///
/// Layout under `root`:
/// ```
/// library.json
/// Assets/cutout-<uuid>.png
/// Assets/spin-<uuid>.png
/// ```
public actor FileOutfitStore: OutfitStore {
    private let root: URL
    private let assetsDirectory: URL
    private let libraryFile: URL
    private let fileManager: FileManager

    /// In-memory mirror of `library.json`, loaded once and kept in step with
    /// every mutation so reads never touch the disk twice.
    private var cached: LibrarySnapshot?

    public init(root: URL, fileManager: FileManager = .default) {
        self.root = root
        self.assetsDirectory = root.appendingPathComponent("Assets", isDirectory: true)
        self.libraryFile = root.appendingPathComponent("library.json")
        self.fileManager = fileManager
    }

    /// Default location: `Application Support/Woo`, excluded from iCloud backup
    /// only if the caller decides to — assets are reproducible, metadata is not.
    public static func defaultRoot(fileManager: FileManager = .default) throws -> URL {
        let support = try fileManager.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        return support.appendingPathComponent("Woo", isDirectory: true)
    }

    // MARK: - Reading

    public func load() async throws -> LibrarySnapshot {
        if let cached { return cached }
        try ensureDirectories()

        guard fileManager.fileExists(atPath: libraryFile.path) else {
            let fresh = LibrarySnapshot.empty
            cached = fresh
            return fresh
        }

        let data = try Data(contentsOf: libraryFile)
        do {
            let snapshot = try Self.decoder.decode(LibrarySnapshot.self, from: data)
            cached = snapshot
            return snapshot
        } catch {
            throw WooError.libraryCorrupted(error.localizedDescription)
        }
    }

    // MARK: - Outfits

    public func addOutfit(_ outfit: Outfit) async throws {
        var snapshot = try await load()
        snapshot.outfits.removeAll { $0.id == outfit.id }
        snapshot.outfits.append(outfit)
        try persist(snapshot)
    }

    public func updateOutfit(_ outfit: Outfit) async throws {
        var snapshot = try await load()
        guard let index = snapshot.outfits.firstIndex(where: { $0.id == outfit.id }) else {
            throw WooError.outfitNotFound(outfit.id)
        }
        snapshot.outfits[index] = outfit
        try persist(snapshot)
    }

    public func deleteOutfit(id: UUID) async throws {
        var snapshot = try await load()
        guard let index = snapshot.outfits.firstIndex(where: { $0.id == id }) else {
            throw WooError.outfitNotFound(id)
        }
        let removed = snapshot.outfits.remove(at: index)
        try persist(snapshot)

        // Assets go after the metadata write: a stray file is harmless, a
        // manifest pointing at a deleted file is not.
        for ref in removed.ownedAssets {
            try? fileManager.removeItem(at: assetURL(ref))
        }
    }

    // MARK: - Wardrobe

    public func addItems(_ items: [GarmentItem]) async throws {
        guard !items.isEmpty else { return }
        var snapshot = try await load()
        let incoming = Set(items.map(\.id))
        snapshot.items.removeAll { incoming.contains($0.id) }
        snapshot.items.append(contentsOf: items)
        try persist(snapshot)
    }

    public func deleteItem(id: UUID) async throws {
        var snapshot = try await load()
        guard let index = snapshot.items.firstIndex(where: { $0.id == id }) else {
            throw WooError.itemNotFound(id)
        }
        let removed = snapshot.items.remove(at: index)
        // Drop the dangling reference from any look that used this piece.
        for i in snapshot.outfits.indices {
            snapshot.outfits[i].itemIDs.removeAll { $0 == id }
        }
        try persist(snapshot)
        try? fileManager.removeItem(at: assetURL(removed.cutout))
    }

    // MARK: - Assets

    public func writeAsset(_ data: Data, ref: AssetRef) async throws {
        try ensureDirectories()
        try data.write(to: assetURL(ref), options: .atomic)
    }

    public func readAsset(_ ref: AssetRef) async throws -> Data {
        let url = assetURL(ref)
        guard fileManager.fileExists(atPath: url.path) else {
            throw WooError.assetNotFound(ref.filename)
        }
        return try Data(contentsOf: url)
    }

    public func deleteAsset(_ ref: AssetRef) async {
        try? fileManager.removeItem(at: assetURL(ref))
    }

    public nonisolated func assetURL(_ ref: AssetRef) -> URL {
        assetsDirectory.appendingPathComponent(ref.filename)
    }

    // MARK: - Plumbing

    private func ensureDirectories() throws {
        for directory in [root, assetsDirectory] where !fileManager.fileExists(atPath: directory.path) {
            try fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
        }
    }

    /// Atomic by construction: a crash mid-write leaves the previous library
    /// intact rather than a half-written file.
    private func persist(_ snapshot: LibrarySnapshot) throws {
        try ensureDirectories()
        let data = try Self.encoder.encode(snapshot)
        try data.write(to: libraryFile, options: .atomic)
        cached = snapshot
    }

    private static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return encoder
    }()

    private static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()
}
