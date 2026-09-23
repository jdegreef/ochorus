import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';
import { SHELVES_KEY } from './reading-schema';
import { readingSync } from './readingSync';
import {
	liveBooks,
	newShelfId,
	SHELF_NAME_MAX,
	type CustomShelf,
	type ShelvesStore
} from './shelvesData';

/**
 * The reader's own Bookshelf shelves ("Lent 2027", "For my small group") —
 * device-local first like every other reading store, mirrored to the account
 * by readingSync when signed in. See shelvesData.ts for the shape and merge.
 *
 * Every change stamps the shelf's `updated` (name / deleted) or the book
 * entry's `at` (add / remove) with this device's clock and pushes the WHOLE
 * shelf; the server merges it per book. A deleted shelf and a removed book
 * stay as entries (tombstones), so no other device can bring them back.
 */
const read = (): ShelvesStore => {
	const raw = readJSON<ShelvesStore>(SHELVES_KEY, {});
	return raw && typeof raw === 'object' ? raw : {};
};

class CustomShelves {
	/** Bumped on every change, and when a sync rewrites the store. */
	ticks = $state(0);

	constructor() {
		if (browser) window.addEventListener('ochorus:sync', () => (this.ticks += 1));
	}

	#save(shelf: CustomShelf) {
		const store = read();
		store[shelf.id] = shelf;
		writeJSON(SHELVES_KEY, store);
		this.ticks += 1;
		readingSync.pushShelf(shelf);
	}

	/** Live shelves, oldest first (the order they were made). */
	list(): CustomShelf[] {
		void this.ticks;
		return Object.values(read())
			.filter((s) => !s.deleted)
			.sort((a, b) => a.created - b.created);
	}

	get(id: string): CustomShelf | null {
		void this.ticks;
		return read()[id] ?? null;
	}

	/** Book slug -> added-at, for a live shelf. */
	books(id: string): Map<string, number> {
		const s = this.get(id);
		return s && !s.deleted ? liveBooks(s) : new Map();
	}

	has(id: string, slug: string): boolean {
		return this.books(id).has(slug);
	}

	/** Make a shelf; returns its id, or null for an empty name. */
	create(name: string, firstBook?: string): string | null {
		const clean = name.trim().slice(0, SHELF_NAME_MAX);
		if (!clean) return null;
		const now = Date.now();
		const id = newShelfId(now);
		this.#save({
			id,
			name: clean,
			deleted: false,
			created: now,
			updated: now,
			books: firstBook ? [{ slug: firstBook, at: now, removed: false }] : []
		});
		return id;
	}

	rename(id: string, name: string): void {
		const s = read()[id];
		const clean = name.trim().slice(0, SHELF_NAME_MAX);
		if (!s || !clean || clean === s.name) return;
		this.#save({ ...s, name: clean, updated: Date.now() });
	}

	/** Delete (tombstone) or restore a shelf — restore is the Undo. */
	setDeleted(id: string, deleted: boolean): void {
		const s = read()[id];
		if (!s || s.deleted === deleted) return;
		this.#save({ ...s, deleted, updated: Date.now() });
	}

	/** Put a book on the shelf, or take it off. */
	setBook(id: string, slug: string, on: boolean): void {
		const s = read()[id];
		if (!s) return;
		const now = Date.now();
		const books = s.books.filter((b) => b.slug !== slug);
		books.push({ slug, at: now, removed: !on });
		this.#save({ ...s, books });
	}
}

export const customShelves = new CustomShelves();
