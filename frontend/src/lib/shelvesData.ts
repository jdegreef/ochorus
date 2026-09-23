/**
 * The reader's own Bookshelf shelves — the data and its merge, with no store
 * (see customShelves.svelte.ts for that). Kept apart so readingSync can merge
 * the account's shelves into localStorage without importing the store, which
 * imports readingSync.
 *
 * The same rules as the API (reading.models.CustomShelf):
 *  - name and deleted state: last-write-wins on `updated` (the writing
 *    device's clock); a tie keeps what's already here;
 *  - the book list: merged PER BOOK — `{slug, at, removed}`, the later `at`
 *    winning — so books added on two devices both stay, and a removal (kept as
 *    an entry with `removed: true`) beats a stale copy of the add.
 */

export interface ShelfBookEntry {
	slug: string;
	/** When this book was last added or removed (epoch ms). */
	at: number;
	removed: boolean;
}

export interface CustomShelf {
	id: string;
	name: string;
	books: ShelfBookEntry[];
	deleted: boolean;
	created: number;
	updated: number;
}

export type ShelvesStore = Record<string, CustomShelf>;

/** The API's shape for a shelf. */
export interface ServerShelf {
	shelf_id: string;
	name: string;
	books: ShelfBookEntry[];
	deleted: boolean;
	client_created_at: string;
	client_updated_at: string;
}

export const SHELF_NAME_MAX = 80;

export function newShelfId(now = Date.now()): string {
	return `s-${now.toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/** Merge `incoming` into `current` by the rules above. */
export function mergeShelf(current: CustomShelf | undefined, incoming: CustomShelf): CustomShelf {
	if (!current) return { ...incoming, books: mergeBooks([], incoming.books) };
	const newer = incoming.updated > current.updated;
	return {
		id: current.id,
		name: newer ? incoming.name : current.name,
		deleted: newer ? incoming.deleted : current.deleted,
		updated: newer ? incoming.updated : current.updated,
		created: Math.min(current.created, incoming.created),
		books: mergeBooks(current.books, incoming.books)
	};
}

function mergeBooks(current: ShelfBookEntry[], incoming: ShelfBookEntry[]): ShelfBookEntry[] {
	const merged = new Map(current.map((b) => [b.slug, b]));
	for (const b of incoming) {
		const cur = merged.get(b.slug);
		if (!cur || b.at > cur.at) merged.set(b.slug, b);
	}
	return [...merged.values()].sort((a, b) => a.at - b.at);
}

/** The shelf's books, `slug -> added at`, removals left out. */
export function liveBooks(shelf: CustomShelf): Map<string, number> {
	return new Map(shelf.books.filter((b) => !b.removed).map((b) => [b.slug, b.at]));
}

export function toServer(s: CustomShelf): ServerShelf & { created_at: number; updated_at: number } {
	return {
		shelf_id: s.id,
		name: s.name,
		books: s.books,
		deleted: s.deleted,
		client_created_at: new Date(s.created).toISOString(),
		client_updated_at: new Date(s.updated).toISOString(),
		// The PUT/merge body's epoch-ms fields.
		created_at: s.created,
		updated_at: s.updated
	};
}

export function fromServer(r: ServerShelf): CustomShelf | null {
	const created = Date.parse(r.client_created_at);
	const updated = Date.parse(r.client_updated_at);
	if (!r.shelf_id || !Number.isFinite(created) || !Number.isFinite(updated)) return null;
	return {
		id: r.shelf_id,
		name: r.name ?? '',
		deleted: !!r.deleted,
		created,
		updated,
		books: Array.isArray(r.books)
			? r.books.filter(
					(b) => b && typeof b.slug === 'string' && typeof b.at === 'number'
				).map((b) => ({ slug: b.slug, at: b.at, removed: !!b.removed }))
			: []
	};
}

/** Fold the account's shelves into the device's (merge, never replace). */
export function mergeServerShelves(local: ShelvesStore, rows: ServerShelf[]): ShelvesStore {
	const out: ShelvesStore = { ...local };
	for (const r of rows) {
		const s = fromServer(r);
		if (s) out[s.id] = mergeShelf(out[s.id], s);
	}
	return out;
}
