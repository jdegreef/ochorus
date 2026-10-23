/**
 * Where the app keeps the reader's Supabase session: the phone's own key-value
 * store (`@capacitor/preferences` — UserDefaults on iOS, SharedPreferences on
 * Android), because iOS may purge a WKWebView's localStorage when the phone is
 * short of space, which would sign the reader out for no reason they can see.
 *
 * The store is the source of truth; localStorage keeps a write-through copy
 * only so the two synchronous readers of the session key still see it before
 * any async code runs — app.html's boot flag and `$lib/auth`'s
 * `storedSessionUser`, which decide what to DRAW at first paint. A purged copy
 * is restored on the next read; a session the store no longer has is dropped
 * from the copy too, so the copy can never claim a reader the store has lost.
 *
 * Pure (no Capacitor import): the store's three calls are handed in, so the
 * website bundle never sees @capacitor/preferences and the test needs no
 * phone. The website keeps supabase-js's default (localStorage) — see index.ts.
 */

/** supabase-js's `SupportedStorage`, the async form. */
export type AuthStorage = {
	getItem(key: string): Promise<string | null>;
	setItem(key: string, value: string): Promise<void>;
	removeItem(key: string): Promise<void>;
};

export type KeyValueStore = {
	prefsGet(key: string): Promise<string | null>;
	prefsSet(key: string, value: string): Promise<void>;
	prefsRemove(key: string): Promise<void>;
};

/** localStorage, never throwing (blocked or full storage is not a sign-in error). */
const copy = {
	get(key: string): string | null {
		try {
			return localStorage.getItem(key);
		} catch {
			return null;
		}
	},
	set(key: string, value: string) {
		try {
			localStorage.setItem(key, value);
		} catch {
			/* the copy is a paint hint only */
		}
	},
	remove(key: string) {
		try {
			localStorage.removeItem(key);
		} catch {
			/* the copy is a paint hint only */
		}
	}
};

export function makeAuthStorage(store: () => Promise<KeyValueStore>): AuthStorage {
	return {
		async getItem(key) {
			let value: string | null;
			try {
				value = await (await store()).prefsGet(key);
			} catch {
				// The store would not answer: the copy is better than signing out.
				return copy.get(key);
			}
			if (value === null) copy.remove(key);
			else if (copy.get(key) !== value) copy.set(key, value);
			return value;
		},
		async setItem(key, value) {
			copy.set(key, value);
			await (await store()).prefsSet(key, value);
		},
		async removeItem(key) {
			copy.remove(key);
			await (await store()).prefsRemove(key);
		}
	};
}
