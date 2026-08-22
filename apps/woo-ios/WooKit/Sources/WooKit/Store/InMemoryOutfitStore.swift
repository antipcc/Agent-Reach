import Foundation

/// Store with no disk behind it — SwiftUI previews and unit tests.
public actor InMemoryOutfitStore: OutfitStore {
    private var snapshot: LibrarySnapshot
    private var assets: [String: Data] = [:]

    public init(snapshot: LibrarySnapshot = .empty) {
        self.snapshot = snapshot
    }

    public func load() async throws -> LibrarySnapshot { snapshot }

    public func addOutfit(_ outfit: Outfit) async throws {
        snapshot.outfits.removeAll { $0.id == outfit.id }
        snapshot.outfits.append(outfit)
    }

    public func updateOutfit(_ outfit: Outfit) async throws {
        guard let index = snapshot.outfits.firstIndex(where: { $0.id == outfit.id }) else {
            throw WooError.outfitNotFound(outfit.id)
        }
        snapshot.outfits[index] = outfit
    }

    public func deleteOutfit(id: UUID) async throws {
        guard let index = snapshot.outfits.firstIndex(where: { $0.id == id }) else {
            throw WooError.outfitNotFound(id)
        }
        let removed = snapshot.outfits.remove(at: index)
        for ref in removed.ownedAssets { assets[ref.filename] = nil }
    }

    public func addItems(_ items: [GarmentItem]) async throws {
        let incoming = Set(items.map(\.id))
        snapshot.items.removeAll { incoming.contains($0.id) }
        snapshot.items.append(contentsOf: items)
    }

    public func deleteItem(id: UUID) async throws {
        guard let index = snapshot.items.firstIndex(where: { $0.id == id }) else {
            throw WooError.itemNotFound(id)
        }
        let removed = snapshot.items.remove(at: index)
        for i in snapshot.outfits.indices {
            snapshot.outfits[i].itemIDs.removeAll { $0 == id }
        }
        assets[removed.cutout.filename] = nil
    }

    public func writeAsset(_ data: Data, ref: AssetRef) async throws {
        assets[ref.filename] = data
    }

    public func readAsset(_ ref: AssetRef) async throws -> Data {
        guard let data = assets[ref.filename] else {
            throw WooError.assetNotFound(ref.filename)
        }
        return data
    }

    public func deleteAsset(_ ref: AssetRef) async {
        assets[ref.filename] = nil
    }

    public nonisolated func assetURL(_ ref: AssetRef) -> URL {
        URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(ref.filename)
    }
}
