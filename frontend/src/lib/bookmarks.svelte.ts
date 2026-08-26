import {
	BOOKMARKS_KEY,
	parseWorkSlugKey,
	workSlugKey,
	type Bookmark,
	type BookmarksStore,
	type WorkKind
} from './reading-schema';
import { readJSON, writeJSON } from './persisted';

/**
 * Explicit bookmarks — places the reader saved on purpose (a paragraph within a
 * work), distinct from the single auto-saved resume point (`progress.ts`) and
 * from text-range highlights (`marks.svelte.ts`). Device-local in localStorage
 * for now; account-sync can follow the marks/progress pattern later.
 *
 * Keyed by `workSlugKey`, so all three long-form kinds can be bookmarked. Books
 * stay under their bare slug, which is what keeps every bookmark saved before
 * this change exactly where it was — the same compatibility rule marks and
 * progress already follow. A sermon and a book may legitimately share a slug,
 * and before the prefix they would have shared a bookmark list.
 *
 * A sermon or biography is a single document: its `order` is always 1
 * (SERMON_CHAPTER_ORDER / BIO_CHAPTER_ORDER), so `p` alone locates the spot.
 */

const readAll = (): BookmarksStore => readJSON<BookmarksStore>(BOOKMARKS_KEY, {});
const writeAll = (store: BookmarksStore) => writeJSON(BOOKMARKS_KEY, store);

const byPosition = (a: Bookmark, b: Bookmark) => a.order - b.order || a.p - b.p;

class Bookmarks {
	/** Reactive bookmarks of the currently open work, in reading order. */
	list = $state<Bookmark[]>([]);
	#key = '';

	load(kind: WorkKind, slug: string) {
		this.#key = workSlugKey(kind, slug);
		this.#hydrate();
	}

	#hydrate() {
		this.list = [...(readAll()[this.#key] ?? [])].sort(byPosition);
	}

	/** Re-read after the cache was replaced underneath us (e.g. sign-in sync). */
	refresh() {
		if (this.#key) this.#hydrate();
	}

	#persist() {
		const store = readAll();
		if (this.list.length === 0) delete store[this.#key];
		else store[this.#key] = this.list;
		writeAll(store);
	}

	find(order: number, p: number): Bookmark | undefined {
		return this.list.find((b) => b.order === order && b.p === p);
	}

	has(order: number, p: number): boolean {
		return this.find(order, p) !== undefined;
	}

	/** Add or remove a bookmark at (order, p). Returns true if it now exists. */
	toggle(order: number, p: number, snippet: string, title: string): boolean {
		const existing = this.find(order, p);
		if (existing) {
			this.remove(existing.id);
			return false;
		}
		const bm: Bookmark = {
			id: `${Date.now().toString(36)}:${order}:${p}`,
			order,
			p,
			snippet,
			title,
			at: Date.now()
		};
		this.list = [...this.list, bm].sort(byPosition);
		this.#persist();
		return true;
	}

	remove(id: string) {
		this.list = this.list.filter((b) => b.id !== id);
		this.#persist();
	}

	/** Every bookmark across every work, for the notebook. */
	all(): (Bookmark & { kind: WorkKind; slug: string })[] {
		const store = readAll();
		return Object.entries(store).flatMap(([key, list]) => {
			const { kind, slug } = parseWorkSlugKey(key);
			return list.map((b) => ({ ...b, kind, slug }));
		});
	}
}

export const bookmarks = new Bookmarks();
