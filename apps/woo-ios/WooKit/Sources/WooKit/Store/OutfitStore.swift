import Foundation

/// Persistence seam for the whole library. The UI only ever talks to this,
/// so the file-backed implementation can be swapped for an in-memory one in
/// tests or a synced one later without touching a single view.
public protocol OutfitStore: Sendable {
    func load() async throws -> LibrarySnapshot

    func addOutfit(_ outfit: Outfit) async throws
    func updateOutfit(_ outfit: Outfit) async throws
    /// Removes the outfit and the assets it owns. Wardrobe items stay.
    func deleteOutfit(id: UUID) async throws

    func addItems(_ items: [GarmentItem]) async throws
    func deleteItem(id: UUID) async throws

    func writeAsset(_ data: Data, ref: AssetRef) async throws
    func readAsset(_ ref: AssetRef) async throws -> Data
    /// Best-effort removal; a missing file is not an error.
    func deleteAsset(_ ref: AssetRef) async
    /// On-disk location of an asset, for handing straight to an image loader.
    func assetURL(_ ref: AssetRef) -> URL
}
