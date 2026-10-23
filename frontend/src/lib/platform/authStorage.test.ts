import { beforeEach, describe, expect, it, vi } from 'vitest';
import { makeAuthStorage } from './authStorage';
import * as platform from './index';

/**
 * The app's session storage: the phone's key-value store is the truth, and
 * localStorage a write-through copy for the synchronous first-paint readers.
 */
const KEY = 'sb-ref-auth-token';
const SESSION = JSON.stringify({ refresh_token: 'r', user: { email: 'grace@example.org' } });

let prefs: Map<string, string>;
const store = {
	prefsGet: vi.fn(async (k: string) => prefs.get(k) ?? null),
	prefsSet: vi.fn(async (k: string, v: string) => void prefs.set(k, v)),
	prefsRemove: vi.fn(async (k: string) => void prefs.delete(k))
};
const storage = makeAuthStorage(async () => store);

beforeEach(() => {
	prefs = new Map();
	localStorage.clear();
	vi.clearAllMocks();
});

describe('authStorage', () => {
	it('is supabase-js’s default (localStorage) on the website', () => {
		expect(platform.authStorage).toBeUndefined();
	});

	it('writes the session to the phone’s store and copies it to localStorage', async () => {
		await storage.setItem(KEY, SESSION);
		expect(store.prefsSet).toHaveBeenCalledWith(KEY, SESSION);
		expect(localStorage.getItem(KEY)).toBe(SESSION);
		expect(await storage.getItem(KEY)).toBe(SESSION);
	});

	it('restores a purged localStorage copy from the store', async () => {
		prefs.set(KEY, SESSION);
		expect(await storage.getItem(KEY)).toBe(SESSION);
		expect(localStorage.getItem(KEY)).toBe(SESSION);
	});

	it('drops a copy the store no longer has, so first paint cannot claim a lost reader', async () => {
		localStorage.setItem(KEY, SESSION);
		expect(await storage.getItem(KEY)).toBeNull();
		expect(localStorage.getItem(KEY)).toBeNull();
	});

	it('removes from both on sign-out', async () => {
		await storage.setItem(KEY, SESSION);
		await storage.removeItem(KEY);
		expect(store.prefsRemove).toHaveBeenCalledWith(KEY);
		expect(prefs.has(KEY)).toBe(false);
		expect(localStorage.getItem(KEY)).toBeNull();
	});

	it('reads the copy when the store will not answer, rather than signing out', async () => {
		localStorage.setItem(KEY, SESSION);
		store.prefsGet.mockRejectedValueOnce(new Error('bridge down'));
		expect(await storage.getItem(KEY)).toBe(SESSION);
	});
});
