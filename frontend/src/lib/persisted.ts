import { browser } from '$app/environment';
import { storageHealth } from './storageHealth.svelte';

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
 * Write a JSON-encoded value to localStorage. A no-op during SSR. The in-memory
 * state is still correct so the reader keeps working this session, but a failure
 * (storage full or disabled in private mode) means the value won't survive a
 * reload — so we flag `storageHealth` to warn the reader rather than losing
 * their highlights/notes/place silently. Returns whether the write succeeded.
 */
export function writeJSON(key: string, value: unknown): boolean {
	if (!browser) return false;
	try {
		localStorage.setItem(key, JSON.stringify(value));
		return true;
	} catch {
		storageHealth.fail();
		return false;
	}
}
