import { browser } from '$app/environment';
import { writeJSON } from './persisted';
import { FAVORITES_KEY as KEY } from './reading-schema';
import { readingSync } from './readingSync';
import { addPending, clearPending } from './removals';

/**
 * The reader's favorites: followed authors, saved books, plans, sermons,
 * topics, articles and individual quotes. Device-local first (localStorage)
 * like every other piece of reading state, mirrored to the account by
 * `readingSync` when signed in — so hearts work offline and survive sign-in
 * via the merge.
 *
 * Stored as `"kind:slug" -> savedAt(ms)`; kinds never contain ':'. A quote's
 * slug is the quote's own permanent address (author slug + text hash); every
 * other kind's slug names its row. Must stay in step with the backend's
 * `FavoriteKind` — the sync PUT 400s on a kind the server doesn't know.
 */

export type FavoriteKind =
	| 'author'
	| 'book'
	| 'plan'
	| 'sermon'
	| 'topic'
	| 'article'
	| 'quote';

export interface FavoriteEntry {
	kind: FavoriteKind;
	slug: string;
	at: number;
}

type Store = Record<string, number>;

const favKey = (kind: FavoriteKind, slug: string) => `${kind}:${slug}`;

/**
 * The stored favorites, parsed once per distinct stored value. Every heart on
 * a page asks `has()` again whenever `ticks` moves, so a tap on one of a quote
 * page's fifty hearts JSON-parsed the whole store fifty times before the frame
 * could paint. Keyed on the raw string, so it is never stale — a write from
 * the sync merge or another tab is a new string, and is parsed fresh. Callers
 * must not mutate the result (toggle copies it).
 */
let cache: { raw: string | null; store: Store } | undefined;
function readAll(): Store {
	if (!browser) return {};
	let raw: string | null;
	try {
		raw = localStorage.getItem(KEY);
	} catch {
		return {};
	}
	if (cache?.raw === raw) return cache.store;
	let store: Store = {};
	try {
		if (raw !== null) store = JSON.parse(raw) as Store;
	} catch {
		/* a corrupt cache reads as empty, as readJSON does */
	}
	cache = { raw, store };
	return store;
}

class Favorites {
	/** Bumped on every mutation so `$derived` consumers refresh. */
	ticks = $state(0);

	constructor() {
		// The cache can be replaced/emptied underneath us (sign-out wipe, sign-in
		// merge) — re-derive open views when that happens.
		if (browser) window.addEventListener('ochorus:sync', () => this.ticks++);
	}

	#write(store: Store) {
		writeJSON(KEY, store);
		this.ticks++;
	}

	has(kind: FavoriteKind, slug: string): boolean {
		void this.ticks;
		return favKey(kind, slug) in readAll();
	}

	/** Flip a favorite; mirrors the change to the account when signed in. */
	toggle(kind: FavoriteKind, slug: string) {
		const store = { ...readAll() };
		const key = favKey(kind, slug);
		const active = !(key in store);
		if (active) store[key] = Date.now();
		else delete store[key];
		this.#write(store);
		// An un-heart is remembered until the account confirms it, so another
		// device's copy can't merge it back (removals.ts); a re-heart lifts it.
		if (active) clearPending('favorite', kind, slug);
		else addPending('favorite', kind, slug);
		readingSync.pushFavorite(kind, slug, active);
	}

	/** Every favorite, most recently saved first. */
	all(): FavoriteEntry[] {
		void this.ticks;
		return Object.entries(readAll())
			.map(([key, at]) => {
				const i = key.indexOf(':');
				return { kind: key.slice(0, i) as FavoriteKind, slug: key.slice(i + 1), at };
			})
			.sort((a, b) => b.at - a.at);
	}

	count(): number {
		void this.ticks;
		return Object.keys(readAll()).length;
	}
}

export const favorites = new Favorites();
