import { browser } from '$app/environment';

/**
 * The one place the reader's localStorage access lives.
 *
 * Every device-local store (progress, marks, bookmarks, reader prefs, plans,
 * listen) previously repeated the same three concerns inline: guard against SSR
 * (no `localStorage`), tolerate a corrupt/absent value on read, and tolerate a
 * failing write (private mode, quota). Centralising them here keeps that
 * contract identical across stores and out of each store's business logic.
 *
 * JSON only — `theme` deliberately persists a bare string and stays on the raw
 * API.
 */

/**
 * Read a JSON-encoded value from localStorage. Returns `fallback` during SSR,
 * when the key is absent, or when the stored value is corrupt — so a bad cache
 * entry can never throw on load.
 */
export function readJSON<T>(key: string, fallback: T): T {
	if (!browser) return fallback;
	try {
		const raw = localStorage.getItem(key);
		return raw === null ? fallback : (JSON.parse(raw) as T);
	} catch {
		return fallback;
	}
}

/**
 * Write a JSON-encoded value to localStorage. A no-op during SSR, and swallows
 * write failures (storage full or disabled) — the in-memory state is still
 * correct, so the reader keeps working for the session.
 */
export function writeJSON(key: string, value: unknown): void {
	if (!browser) return;
	try {
		localStorage.setItem(key, JSON.stringify(value));
	} catch {
		/* quota exceeded or storage disabled — ignore */
	}
}
