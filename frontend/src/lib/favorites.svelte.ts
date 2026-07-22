import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';
import { FAVORITES_KEY as KEY } from './reading-schema';
import { readingSync } from './readingSync';

/**
 * The reader's favorites: followed authors, saved books and plans (and
 * sermons). Device-local first (localStorage) like every other piece of
 * reading state, mirrored to the account by `readingSync` when signed in —
 * so hearts work offline and survive sign-in via the merge.
 *
 * Stored as `"kind:slug" -> savedAt(ms)`; kinds never contain ':'.
 */

export type FavoriteKind = 'author' | 'book' | 'plan' | 'sermon';

export interface FavoriteEntry {
	kind: FavoriteKind;
	slug: string;
	at: number;
}

type Store = Record<string, number>;

const favKey = (kind: FavoriteKind, slug: string) => `${kind}:${slug}`;

const readAll = (): Store => readJSON<Store>(KEY, {});

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
		const store = readAll();
		const key = favKey(kind, slug);
		const active = !(key in store);
		if (active) store[key] = Date.now();
		else delete store[key];
		this.#write(store);
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
