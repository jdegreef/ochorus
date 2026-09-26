import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { readingSync } from './readingSync';
import {
	READING_DATA_KEYS,
	SIGN_OUT_DATA_KEYS,
	BOOKMARKS_KEY,
	PROGRESS_KEY,
	MARKS_KEY,
	LAST_SYNC_KEY,
	FAVORITES_KEY,
	JOURNAL_KEY,
	JOURNAL_DIRTY_KEY,
	SHELVES_KEY,
	SYNC_OWED_KEY,
	SYNC_STASH_KEY
} from './reading-schema';
import { addPending, bookmarkTarget, pendingAt } from './removals';

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
		const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(
			async () => new Response('{}', { status: 200 })
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

			addPending('bookmark', 'book', bookmarkTarget('humility', 2, 5), 555);
			readingSync.removeBookmark('book', 'humility', 2, 5);
			await vi.runAllTimersAsync();
			const [url2, init2] = fetchSpy.mock.calls[1];
			// The removal carries this device's clock, and clears once it lands.
			expect(String(url2)).toContain('/api/reading/bookmarks/book/humility/2/5/?at=555');
			expect(init2?.method).toBe('DELETE');
			await vi.waitFor(() =>
				expect(pendingAt('bookmark', 'book', bookmarkTarget('humility', 2, 5))).toBeNull()
			);
		} finally {
			fetchSpy.mockRestore();
			vi.useRealTimers();
			readingSync.setSignedIn(false);
		}
	});

	it('removeProgress DELETEs with the removal clock and clears its pending entry', async () => {
		const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
			new Response(null, { status: 204 })
		);
		try {
			readingSync.setSignedIn(true);
			const at = addPending('progress', 'book', 'humility', 777);
			readingSync.removeProgress('book', 'humility', at);
			await vi.waitFor(() => expect(pendingAt('progress', 'book', 'humility')).toBeNull());
			const [url, init] = fetchSpy.mock.calls[0];
			expect(String(url)).toContain('/api/reading/progress/humility/?kind=book&at=777');
			expect(init?.method).toBe('DELETE');
		} finally {
			fetchSpy.mockRestore();
			readingSync.setSignedIn(false);
		}
	});

	it('the merge carries pending removals and heart times, and clears only when applied', async () => {
		localStorage.setItem(FAVORITES_KEY, JSON.stringify({ 'book:humility': 42 }));
		localStorage.setItem(
			BOOKMARKS_KEY,
			JSON.stringify({ 'book:humility': [{ id: 'x', order: 2, p: 5, snippet: '', title: '', at: 64 }] })
		);
		addPending('favorite', 'author', 'andrew-murray', 99);
		const reply = (applied: boolean) =>
			new Response(
				JSON.stringify({ progress: [], marks: [], favorites: [], ...(applied ? { removed_applied: true } : {}) }),
				{ status: 200, headers: { 'content-type': 'application/json' } }
			);
		const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(reply(false));
		try {
			readingSync.setSignedIn(true);
			await readingSync.mergeOnSignIn();
			const body = JSON.parse(String(fetchSpy.mock.calls[0][1]?.body));
			expect(body.favorites).toEqual([{ kind: 'book', slug: 'humility', saved_at: 42 }]);
			expect(body.bookmarks[0]).toMatchObject({ chapter_order: 2, paragraph_index: 5, saved_at: 64 });
			expect(body.removed).toEqual([{ domain: 'favorite', kind: 'author', slug: 'andrew-murray', at: 99 }]);
			// An API from before tombstones ignored them — keep them for next time.
			expect(pendingAt('favorite', 'author', 'andrew-murray')).toBe(99);

			fetchSpy.mockResolvedValueOnce(reply(true));
			await readingSync.mergeOnSignIn();
			expect(pendingAt('favorite', 'author', 'andrew-murray')).toBeNull();
		} finally {
			fetchSpy.mockRestore();
			readingSync.setSignedIn(false);
		}
	});

	it('the merge sends every shelf and merges the reply into the device copy', async () => {
		const local = {
			's-a': { id: 's-a', name: 'Lent', books: [{ slug: 'x', at: 5, removed: false }], deleted: false, created: 1, updated: 1 }
		};
		localStorage.setItem(SHELVES_KEY, JSON.stringify(local));
		const server = {
			shelf_id: 's-b',
			name: 'From the phone',
			books: [],
			deleted: false,
			client_created_at: new Date(2).toISOString(),
			client_updated_at: new Date(2).toISOString()
		};
		const reply = (shelves?: unknown[]) =>
			new Response(JSON.stringify({ progress: [], marks: [], ...(shelves ? { shelves } : {}) }), {
				status: 200,
				headers: { 'content-type': 'application/json' }
			});
		const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(reply([server]));
		try {
			readingSync.setSignedIn(true);
			await readingSync.mergeOnSignIn();
			const body = JSON.parse(String(fetchSpy.mock.calls[0][1]?.body));
			expect(body.shelves.map((s: { shelf_id: string }) => s.shelf_id)).toEqual(['s-a']);
			expect(Object.keys(JSON.parse(localStorage.getItem(SHELVES_KEY)!)).sort()).toEqual(['s-a', 's-b']);

			// An API from before shelves sends none — the device's are kept.
			fetchSpy.mockResolvedValueOnce(reply());
			await readingSync.mergeOnSignIn();
			expect(Object.keys(JSON.parse(localStorage.getItem(SHELVES_KEY)!)).sort()).toEqual(['s-a', 's-b']);
		} finally {
			fetchSpy.mockRestore();
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

describe('readingSync.flushJournal', () => {
	const entry = (id: string, updatedAt: number) => ({
		id,
		kind: 'note',
		title: '',
		body: id,
		ref: '',
		person: '',
		group: '',
		remind: '',
		updates: [],
		source: null,
		answer: '',
		answeredAt: null,
		createdAt: 1000,
		updatedAt
	});
	const seed = () => {
		localStorage.setItem(JOURNAL_KEY, JSON.stringify({ a: entry('a', 2000), b: entry('b', 3000) }));
		localStorage.setItem(JOURNAL_DIRTY_KEY, JSON.stringify({ a: 2000, b: 3000, gone: 5 }));
	};

	afterEach(() => {
		vi.restoreAllMocks();
		readingSync.setSignedIn(false);
	});

	it('delivers what the account is owed, newest first, and stops owing it', async () => {
		seed();
		const fetchSpy = vi
			.spyOn(globalThis, 'fetch')
			.mockImplementation(async () => new Response('{}', { status: 200 }));
		readingSync.setSignedIn(true);
		await expect(readingSync.flushJournal()).resolves.toBe(true);
		expect(fetchSpy.mock.calls.map(([url]) => String(url).match(/journal\/(\w+)\//)?.[1])).toEqual(['b', 'a']);
		// An owed id with no entry left on the device can never be delivered.
		expect(readingSync.pendingJournal()).toEqual({});
	});

	it('stops at the first failure and keeps the rest owed', async () => {
		seed();
		vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'));
		readingSync.setSignedIn(true);
		await expect(readingSync.flushJournal()).resolves.toBe(false);
		expect(Object.keys(readingSync.pendingJournal()).sort()).toEqual(['a', 'b', 'gone']);
	});

	it('does nothing signed out', async () => {
		seed();
		const fetchSpy = vi.spyOn(globalThis, 'fetch');
		await expect(readingSync.flushJournal()).resolves.toBe(false);
		expect(fetchSpy).not.toHaveBeenCalled();
	});
});

describe('readingSync — nothing lost at sign-out', () => {
	const ok = () => new Response('{}', { status: 200 });
	const mergeReply = (marks: unknown[] = []) =>
		new Response(JSON.stringify({ progress: [], marks, favorites: [] }), {
			status: 200,
			headers: { 'content-type': 'application/json' }
		});
	const rec = { order: 3, paragraph_index: 5, language: 'en', at: 1 };

	afterEach(() => {
		vi.restoreAllMocks();
		readingSync.setSignedIn(false);
	});

	it('settle sends a push still waiting on its debounce, and resolves true', async () => {
		const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(ok());
		readingSync.setSignedIn(true);
		readingSync.pushProgress('book', 'humility', rec);
		expect(readingSync.hasUnsynced()).toBe(true);
		await expect(readingSync.settle()).resolves.toBe(true);
		expect(String(fetchSpy.mock.calls[0][0])).toContain('/api/reading/progress/humility/');
		expect(readingSync.hasUnsynced()).toBe(false);
	});

	it('a failed push is owed; settle merges to recover it', async () => {
		const fetchSpy = vi
			.spyOn(globalThis, 'fetch')
			.mockRejectedValueOnce(new TypeError('offline'))
			.mockResolvedValueOnce(mergeReply());
		readingSync.setSignedIn(true);
		readingSync.pushProgress('book', 'humility', rec);
		await expect(readingSync.settle()).resolves.toBe(true);
		expect(String(fetchSpy.mock.calls[1][0])).toContain('/api/reading/merge/');
		expect(localStorage.getItem(SYNC_OWED_KEY)).toBeNull();
	});

	it('settle resolves false while the account still cannot be reached', async () => {
		vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'));
		readingSync.setSignedIn(true);
		readingSync.pushProgress('book', 'humility', rec);
		await expect(readingSync.settle()).resolves.toBe(false);
		expect(localStorage.getItem(SYNC_OWED_KEY)).not.toBeNull();
	});

	it('a merge keeps a highlight made while it was in flight', async () => {
		const before = { 'humility:1': { m: [] } };
		const during = { 'humility:1': { m: [{ id: 'new', s: [[0, 0, 4]], c: 'y' }] } };
		localStorage.setItem(MARKS_KEY, JSON.stringify(before));
		vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
			// The reader highlights while the request is out.
			localStorage.setItem(MARKS_KEY, JSON.stringify(during));
			return mergeReply([{ kind: 'book', book_slug: 'humility', chapter_order: 1, marks: [] }]);
		});
		readingSync.setSignedIn(true);
		await readingSync.mergeOnSignIn();
		expect(JSON.parse(localStorage.getItem(MARKS_KEY)!)['humility:1']).toEqual(during['humility:1']);
	});

	it('an involuntary session end sets unsynced data aside for the same account only', () => {
		localStorage.setItem(MARKS_KEY, JSON.stringify({ 'humility:1': { m: [] } }));
		localStorage.setItem(SYNC_OWED_KEY, '1');
		readingSync.endSession('a@example.com');
		// Wiped like any sign-out…
		expect(localStorage.getItem(MARKS_KEY)).toBeNull();
		expect(localStorage.getItem(SYNC_STASH_KEY)).not.toBeNull();
		// …and handed back only to the account it came from.
		readingSync.restoreStash('someone-else@example.com');
		expect(localStorage.getItem(MARKS_KEY)).toBeNull();
		expect(localStorage.getItem(SYNC_STASH_KEY)).toBeNull();
	});

	it('restoreStash gives the data back to the same account', () => {
		localStorage.setItem(MARKS_KEY, JSON.stringify({ 'humility:1': { m: [] } }));
		localStorage.setItem(SYNC_OWED_KEY, '1');
		readingSync.endSession('a@example.com');
		readingSync.restoreStash('a@example.com');
		expect(JSON.parse(localStorage.getItem(MARKS_KEY)!)).toEqual({ 'humility:1': { m: [] } });
		expect(localStorage.getItem(SYNC_STASH_KEY)).toBeNull();
	});

	it('nothing is stashed when the account already has everything', () => {
		localStorage.setItem(MARKS_KEY, JSON.stringify({ 'humility:1': { m: [] } }));
		readingSync.endSession('a@example.com');
		expect(localStorage.getItem(SYNC_STASH_KEY)).toBeNull();
	});
});
