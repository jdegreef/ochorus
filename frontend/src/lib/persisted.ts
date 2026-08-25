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

/**
 * Re-broadcast another tab's localStorage writes as `ochorus:sync`.
 *
 * The `storage` event fires only in the OTHER tabs, which is exactly what was
 * missing: every reading store is a read-modify-write over a whole JSON blob, so
 * two tabs open on Ochorus — a chapter in one, the notebook in the other — drift
 * apart, and the last full-blob write wins. A highlight made in tab A is
 * destroyed when tab B saves a scroll anchor.
 *
 * `ochorus:sync` is reused rather than invented: every store and component that
 * needs to re-read already listens for it (it is what a sign-in merge fires), so
 * one listener here reaches all of them. That fixes STALENESS — each listener
 * re-reads from localStorage, which now holds the other tab's value. The
 * lost-update half additionally needs each mutating store to re-read
 * immediately before it writes; they mostly do.
 *
 * Registered once at module load: this module is imported by every store, and a
 * per-store registration would multiply the work on every event.
 */
if (browser) {
	window.addEventListener('storage', (event) => {
		// `key === null` is a whole-storage clear (another tab signed out), which
		// every store must also notice. Otherwise only our own keys matter — an
		// unrelated app on the same origin must not spin the reader.
		if (event.key === null || event.key.startsWith('ochorus:')) {
			window.dispatchEvent(new CustomEvent('ochorus:sync'));
		}
	});
}
