import SwiftUI
import UIKit
import WooKit

/// Everything the views read and every action they can take, held on the main
/// actor. The heavy lifting stays in `LibraryService`; this is the thin,
/// observable skin over it.
@MainActor
@Observable
final class LibraryModel {
    /// A running 360° generation. Survives being minimised — the point of the
    /// Minimize button is that the app stays usable while a model works.
    struct SpinJob: Equatable {
        let outfitID: UUID
        let preview: AssetRef
        var progress: Double
        var isMinimized: Bool
    }

    private(set) var outfits: [Outfit] = []
    private(set) var items: [GarmentItem] = []
    private(set) var isLoading = true
    private(set) var spinJob: SpinJob?

    /// Surfaced as a banner; set to nil to dismiss.
    var errorMessage: String?
    /// Which look the home card is showing.
    var selectedOutfitID: UUID?

    let service: LibraryService
    /// Kept alongside the service so views can resolve a file URL to share
    /// without hopping through an actor.
    let store: any OutfitStore
    /// True while the mocks are in charge, so the UI can say so honestly.
    let isUsingMockModels: Bool

    private var spinTask: Task<Void, Never>?

    init(service: LibraryService, store: any OutfitStore, isUsingMockModels: Bool) {
        self.service = service
        self.store = store
        self.isUsingMockModels = isUsingMockModels
    }

    func assetURL(_ ref: AssetRef) -> URL { store.assetURL(ref) }

    // MARK: - Reading

    var selectedOutfit: Outfit? {
        guard let selectedOutfitID else { return outfits.first }
        return outfits.first { $0.id == selectedOutfitID } ?? outfits.first
    }

    var selectedIndex: Int? {
        guard let selected = selectedOutfit else { return nil }
        return outfits.firstIndex { $0.id == selected.id }
    }

    var isEmpty: Bool { outfits.isEmpty && !isLoading }

    func items(in outfit: Outfit) -> [GarmentItem] {
        // Preserve the outfit's own order rather than the wardrobe's.
        outfit.itemIDs.compactMap { id in items.first { $0.id == id } }
    }

    func outfit(on day: Date, calendar: Calendar = .current) -> Outfit? {
        outfits.first { calendar.isDate($0.date, inSameDayAs: day) }
    }

    func itemsByCategory() -> [WardrobeSection] {
        LibrarySnapshot(outfits: outfits, items: items).itemsByCategory()
    }

    // MARK: - Loading

    func refresh() async {
        do {
            let snapshot = try await service.snapshot()
            outfits = snapshot.outfitsNewestFirst
            items = snapshot.items
            if selectedOutfitID == nil || !outfits.contains(where: { $0.id == selectedOutfitID }) {
                selectedOutfitID = outfits.first?.id
            }
        } catch {
            report(error)
        }
        isLoading = false
    }

    // MARK: - Paging

    func showPrevious() {
        guard let index = selectedIndex, index > 0 else { return }
        selectedOutfitID = outfits[index - 1].id
    }

    func showNext() {
        guard let index = selectedIndex, index < outfits.count - 1 else { return }
        selectedOutfitID = outfits[index + 1].id
    }

    var canShowPrevious: Bool { (selectedIndex ?? 0) > 0 }
    var canShowNext: Bool { (selectedIndex ?? outfits.count) < outfits.count - 1 }

    // MARK: - Capture

    /// Photo in, saved look out: cutout, palette, and the pieces filed in the
    /// wardrobe. Garment extraction failing does not lose the look.
    @discardableResult
    func ingest(_ image: UIImage, date: Date = Date(), source: OutfitSource = .camera) async -> Outfit? {
        guard let data = image.jpegData(compressionQuality: 0.92) else {
            errorMessage = "That photo could not be read."
            return nil
        }

        do {
            let outfit = try await service.ingestPhoto(.jpeg(data), date: date, source: source)
            await refresh()
            selectedOutfitID = outfit.id

            do {
                _ = try await service.extractGarments(for: outfit.id)
                await refresh()
            } catch {
                // The look is already saved; say what went wrong and move on.
                report(error)
            }
            return outfit
        } catch {
            report(error)
            return nil
        }
    }

    // MARK: - Edits

    func delete(_ outfit: Outfit) async {
        do {
            try await service.deleteOutfit(id: outfit.id)
            if spinJob?.outfitID == outfit.id { cancelSpin() }
            await refresh()
        } catch {
            report(error)
        }
    }

    func deleteItem(_ item: GarmentItem) async {
        do {
            try await service.deleteItem(id: item.id)
            await refresh()
        } catch {
            report(error)
        }
    }

    // MARK: - 360°

    func startSpin(for outfit: Outfit) {
        guard spinJob == nil else { return }
        spinJob = SpinJob(outfitID: outfit.id, preview: outfit.cutout, progress: 0, isMinimized: false)

        spinTask = Task { [weak self] in
            guard let self else { return }
            do {
                _ = try await self.service.generateSpin(
                    for: outfit.id,
                    progress: { value in
                        Task { @MainActor [weak self] in
                            self?.spinJob?.progress = value
                        }
                    }
                )
                await self.refresh()
                self.selectedOutfitID = outfit.id
            } catch is CancellationError {
                // Cancelled by the user; nothing to report.
            } catch {
                self.report(error)
            }
            self.spinJob = nil
        }
    }

    func minimizeSpin() { spinJob?.isMinimized = true }
    func restoreSpin() { spinJob?.isMinimized = false }

    func cancelSpin() {
        spinTask?.cancel()
        spinTask = nil
        spinJob = nil
    }

    // MARK: - Try-on

    func tryOn(person: UIImage, itemIDs: [UUID], progress: @escaping @Sendable (Double) -> Void) async -> UIImage? {
        guard let data = person.jpegData(compressionQuality: 0.92) else {
            errorMessage = "That photo could not be read."
            return nil
        }
        do {
            let result = try await service.tryOn(person: .jpeg(data), itemIDs: itemIDs, progress: progress)
            return UIImage(data: result.data)
        } catch {
            report(error)
            return nil
        }
    }

    func saveTryOnResult(_ image: UIImage, itemIDs: [UUID]) async {
        guard let data = image.pngData() else { return }
        do {
            let outfit = try await service.saveTryOnResult(.png(data), itemIDs: itemIDs, isFavorite: true)
            await refresh()
            selectedOutfitID = outfit.id
        } catch {
            report(error)
        }
    }

    // MARK: - Errors

    private func report(_ error: Error) {
        errorMessage = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
    }
}
