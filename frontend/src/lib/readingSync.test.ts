import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { readingSync } from './readingSync';
import {
	READING_DATA_KEYS,
	SIGN_OUT_DATA_KEYS,
	BOOKMARKS_KEY,
	PROGRESS_KEY,
	MARKS_KEY,
	LAST_SYNC_KEY
} from './reading-schema';

beforeEach(() => localStorage.clear());

describe('readingSync last-synced', () => {
	it('parses the stored timestamp, and returns null when absent or garbage', () => {
		expect(readingSync.readLastSynced()).toBeNull();
		localStorage.setItem(LAST_SYNC_KEY, String(1_750_000_000_000));
		expect(readingSync.readLastSynced()).toBe(1_750_000_000_000);
		localStorage.setItem(LAST_SYNC_KEY, 'nonsense');
		expect(readingSync.readLastSynced()).toBeNull();
	});

	it('syncNow is a no-op that resolves false when signed out', async () => {
		readingSync.setSignedIn(false);
		await expect(readingSync.syncNow()).resolves.toBe(false);
	});

	it('clearOnSignOut wipes the last-synced timestamp', () => {
		localStorage.setItem(LAST_SYNC_KEY, String(1_750_000_000_000));
		readingSync.clearOnSignOut();
		expect(localStorage.getItem(LAST_SYNC_KEY)).toBeNull();
	});
});

describe('readingSync.clearOnSignOut', () => {
	it('removes all reading data (bookmarks now sync) but keeps device prefs', () => {
		for (const key of READING_DATA_KEYS) localStorage.setItem(key, '{"some":"data"}');
		localStorage.setItem('ochorus:reader-prefs', '{"scale":1.2}');
		localStorage.setItem('ochorus:lang', 'lg');

		readingSync.clearOnSignOut();

		for (const key of SIGN_OUT_DATA_KEYS) expect(localStorage.getItem(key)).toBeNull();
		// Bookmarks now have a server copy, so a sign-out clears them like the rest
		// (the account keeps them) — no shared-device leak into the next merge.
		expect(localStorage.getItem(BOOKMARKS_KEY)).toBeNull();
		// Theme/font/language are device preferences, not identity data.
		expect(localStorage.getItem('ochorus:reader-prefs')).toBe('{"scale":1.2}');
		expect(localStorage.getItem('ochorus:lang')).toBe('lg');
	});

	it('clearDeviceData (explicit "clear reading data") also removes bookmarks', () => {
		for (const key of READING_DATA_KEYS) localStorage.setItem(key, '{"some":"data"}');

		readingSync.clearDeviceData();

		for (const key of READING_DATA_KEYS) expect(localStorage.getItem(key)).toBeNull();
	});

	it('notifies open views that the cache was emptied', () => {
		const onSync = vi.fn();
		window.addEventListener('ochorus:sync', onSync);
		readingSync.clearOnSignOut();
		window.removeEventListener('ochorus:sync', onSync);
		expect(onSync).toHaveBeenCalledTimes(1);
	});

	it('cancels pending debounced pushes so none fire after sign-out', () => {
		vi.useFakeTimers();
		const fetchSpy = vi.spyOn(globalThis, 'fetch');
		try {
			readingSync.setSignedIn(true);
			readingSync.pushProgress('book', 'humility', {
				order: 3,
				paragraph_index: 5,
				language: 'en',
				at: Date.now()
			});
			readingSync.clearOnSignOut();
			vi.runAllTimers();
			expect(fetchSpy).not.toHaveBeenCalled();
		} finally {
			fetchSpy.mockRestore();
			vi.useRealTimers();
			readingSync.setSignedIn(false);
		}
	});

	it('pushProgress sends the record\'s client timestamp for recency', async () => {
		const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
			new Response('{}', { status: 200 })
		);
		vi.useFakeTimers();
		try {
			readingSync.setSignedIn(true);
			readingSync.pushProgress('book', 'humility', {
				order: 8,
				paragraph_index: 2,
				language: 'en',
				at: 1234
			});
			await vi.runAllTimersAsync();
			const [url, init] = fetchSpy.mock.calls[0];
			expect(String(url)).toContain('/api/reading/progress/humility/');
			// The server keeps a newer position when a stale tab flushes late, so
			// the push must carry the record's client time.
			expect(JSON.parse(String(init?.body))).toMatchObject({ chapter_order: 8, updated_at: 1234 });
		} finally {
			fetchSpy.mockRestore();
			vi.useRealTimers();
			readingSync.setSignedIn(false);
		}
	});

	it('pushPlan PUTs a plan\'s progress when signed in', async () => {
		const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
			new Response('{}', { status: 200 })
		);
		vi.useFakeTimers();
		try {
			readingSync.setSignedIn(true);
			readingSync.pushPlan('school-of-prayer', { startedAt: 1000, done: [1, 2, 3] });
			await vi.runAllTimersAsync();
			expect(fetchSpy).toHaveBeenCalledTimes(1);
			const [url, init] = fetchSpy.mock.calls[0];
			expect(String(url)).toContain('/api/reading/plan/school-of-prayer/');
			expect(init?.method).toBe('PUT');
			expect(JSON.parse(String(init?.body))).toEqual({ started_at: 1000, done: [1, 2, 3] });
		} finally {
			fetchSpy.mockRestore();
			vi.useRealTimers();
			readingSync.setSignedIn(false);
		}
	});

	it('does not push a plan when signed out', () => {
		const fetchSpy = vi.spyOn(globalThis, 'fetch');
		vi.useFakeTimers();
		try {
			readingSync.setSignedIn(false);
			readingSync.pushPlan('x', { startedAt: 1, done: [1] });
			vi.runAllTimers();
			expect(fetchSpy).not.toHaveBeenCalled();
		} finally {
			fetchSpy.mockRestore();
			vi.useRealTimers();
		}
	});

	it('pushBookmark PUTs a saved paragraph, removeBookmark DELETEs it', async () => {
		const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
			new Response('{}', { status: 200 })
		);
		vi.useFakeTimers();
		try {
			readingSync.setSignedIn(true);
			readingSync.pushBookmark('book', 'humility', {
				id: 'abc',
				order: 2,
				p: 5,
				snippet: 'Blessed',
				title: 'Ch 2',
				at: 111
			});
			await vi.runAllTimersAsync();
			const [url, init] = fetchSpy.mock.calls[0];
			expect(String(url)).toContain('/api/reading/bookmarks/book/humility/2/5/');
			expect(init?.method).toBe('PUT');
			expect(JSON.parse(String(init?.body))).toEqual({
				bm_id: 'abc',
				snippet: 'Blessed',
				title: 'Ch 2'
			});

			readingSync.removeBookmark('book', 'humility', 2, 5);
			await vi.runAllTimersAsync();
			const [url2, init2] = fetchSpy.mock.calls[1];
			expect(String(url2)).toContain('/api/reading/bookmarks/book/humility/2/5/');
			expect(init2?.method).toBe('DELETE');
		} finally {
			fetchSpy.mockRestore();
			vi.useRealTimers();
			readingSync.setSignedIn(false);
		}
	});

	it('leaves the next sign-in with an empty local cache to merge', () => {
		localStorage.setItem(PROGRESS_KEY, '{"humility":{"order":3}}');
		localStorage.setItem(MARKS_KEY, '{"humility:3":{"m":[]}}');
		readingSync.clearOnSignOut();
		// mergeOnSignIn reads these keys directly; after a wipe the previous
		// user's state must not be part of the next account's merge payload.
		expect(localStorage.getItem(PROGRESS_KEY)).toBeNull();
		expect(localStorage.getItem(MARKS_KEY)).toBeNull();
	});
});

describe('readingSync.fetchProgress', () => {
	const row = (client_updated_at: string | null) =>
		new Response(
			JSON.stringify({
				kind: 'book',
				book_slug: 'humility',
				language: 'en',
				chapter_order: 7,
				paragraph_index: 3,
				updated_at: '2024-01-01T10:00:00.000000Z',
				client_updated_at
			}),
			{ status: 200, headers: { 'content-type': 'application/json' } }
		);

	afterEach(() => vi.unstubAllGlobals());

	it('does not even ask when signed out', async () => {
		const fetchSpy = vi.fn();
		vi.stubGlobal('fetch', fetchSpy);
		readingSync.setSignedIn(false);
		await expect(readingSync.fetchProgress('book', 'humility')).resolves.toBeNull();
		expect(fetchSpy).not.toHaveBeenCalled();
	});

	it("returns the row with `at` from the writing device's own clock", async () => {
		vi.stubGlobal('fetch', vi.fn(async () => row('2024-01-01T09:58:00.000000Z')));
		readingSync.setSignedIn(true);
		const rec = await readingSync.fetchProgress('book', 'humility');
		expect(rec).toEqual({
			order: 7,
			paragraph_index: 3,
			language: 'en',
			at: Date.parse('2024-01-01T09:58:00.000Z'),
			finished_at: null
		});
	});

	it('falls back to the server clock for a row an old client wrote without one', async () => {
		vi.stubGlobal('fetch', vi.fn(async () => row(null)));
		readingSync.setSignedIn(true);
		const rec = await readingSync.fetchProgress('book', 'humility');
		expect(rec?.at).toBe(Date.parse('2024-01-01T10:00:00.000Z'));
	});

	it('answers null for no position (404) and for a network failure', async () => {
		vi.stubGlobal('fetch', vi.fn(async () => new Response('{"detail":"No position."}', { status: 404 })));
		readingSync.setSignedIn(true);
		await expect(readingSync.fetchProgress('book', 'humility')).resolves.toBeNull();
		vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('offline'); }));
		await expect(readingSync.fetchProgress('book', 'humility')).resolves.toBeNull();
	});
});
