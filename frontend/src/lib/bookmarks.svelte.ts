import { BOOKMARKS_KEY, type Bookmark, type BookmarksStore } from './reading-schema';
import { readJSON, writeJSON } from './persisted';

/**
 * Explicit bookmarks — places the reader saved on purpose (a chapter + paragraph),
 * distinct from the single auto-saved resume point (`progress.ts`) and from
 * text-range highlights (`marks.svelte.ts`). Device-local in localStorage for
 * now; account-sync can follow the marks/progress pattern later.
 */

const readAll = (): BookmarksStore => readJSON<BookmarksStore>(BOOKMARKS_KEY, {});
const writeAll = (store: BookmarksStore) => writeJSON(BOOKMARKS_KEY, store);

const byPosition = (a: Bookmark, b: Bookmark) => a.order - b.order || a.p - b.p;

class Bookmarks {
	/** Reactive bookmarks of the currently open book, in reading order. */
	list = $state<Bookmark[]>([]);
	#slug = '';

	load(slug: string) {
		this.#slug = slug;
		this.#hydrate();
	}

	#hydrate() {
		this.list = [...(readAll()[this.#slug] ?? [])].sort(byPosition);
	}

	/** Re-read after the cache was replaced underneath us (e.g. sign-in sync). */
	refresh() {
		if (this.#slug) this.#hydrate();
	}

	#persist() {
		const store = readAll();
		if (this.list.length === 0) delete store[this.#slug];
		else store[this.#slug] = this.list;
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

	/** Every bookmark across all books, for the notebook. */
	all(): (Bookmark & { slug: string })[] {
		const store = readAll();
		return Object.entries(store).flatMap(([slug, list]) =>
			list.map((b) => ({ ...b, slug }))
		);
	}
}

export const bookmarks = new Bookmarks();
