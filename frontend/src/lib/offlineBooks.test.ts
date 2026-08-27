import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { coverVariants } from './coverArt';
import { offlineBooks } from './offlineBooks.svelte';

const KEY = 'ochorus:offline-books';

beforeEach(() => localStorage.clear());

/** Absolute form of a URL, the shape a Request carries. */
const abs = (u: string) => new URL(u, 'https://api.test').href;

/**
 * A minimal Cache API over a set of URLs. jsdom has none, and `remove()` bails
 * before touching storage without one — so the deletion behaviour under test
 * here (which entries go, which stay) is unreachable otherwise.
 */
function fakeCaches(urls: string[]): Set<string> {
	const store = new Set(urls.map(abs));
	const cache = {
		keys: async () => [...store].map((u) => new Request(u)),
		delete: async (req: Request | string) => store.delete(abs(typeof req === 'string' ? req : req.url)),
		put: async () => {},
		match: async () => undefined
	};
	vi.stubGlobal('caches', { open: async () => cache });
	return store;
}

afterEach(() => vi.unstubAllGlobals());


describe('offlineBooks tracking', () => {
	it('is empty on a fresh device', () => {
		expect(offlineBooks.list()).toEqual([]);
		expect(offlineBooks.has('godliness', 'en')).toBe(false);
	});

	it('reflects the stored metadata, newest first', () => {
		localStorage.setItem(
			KEY,
			JSON.stringify([
				{ slug: 'a', title: 'A', author: 'X', coverUrl: '', language: 'en', chapterCount: 3, at: 100 },
				{ slug: 'b', title: 'B', author: 'Y', coverUrl: '', language: 'en', chapterCount: 5, at: 200 }
			])
		);
		expect(offlineBooks.list().map((b) => b.slug)).toEqual(['b', 'a']);
		expect(offlineBooks.has('a', 'en')).toBe(true);
		expect(offlineBooks.has('c', 'en')).toBe(false);
	});

	it('download is a no-op without the Cache API (jsdom has none)', async () => {
		const ok = await offlineBooks.download({
			slug: 'godliness',
			title: 'Godliness',
			language: 'en',
			cover_url: '',
			author: { name: 'Catherine Booth' },
			chapters: [{ order: 1 }, { order: 2 }]
		});
		expect(ok).toBe(false);
		expect(offlineBooks.has('godliness', 'en')).toBe(false);
	});

	it('downloads the cover files the browser will actually ask for', () => {
		// `BookCover` requests a variant through srcset and never the original, so
		// a download that cached `cover_url` alone put nothing in the durable cache
		// that a render would hit — the variant landed in the versioned cache
		// instead, which the service worker drops on the next deploy, and the book
		// lost its cover offline. jsdom has no Cache API, so this pins the URL set
		// the download derives rather than the fetches.
		expect(coverVariants('/covers/godliness.jpg')).toEqual([
			'/covers/godliness-320.webp',
			'/covers/godliness-640.webp'
		]);
		expect(coverVariants('/covers/all-of-grace.svg')).toEqual([]);
	});
});

describe('a download is one book in one language (#1073)', () => {
	// Every cached URL already carried `?language=`, so the BYTES were always
	// per-language. Only the tracking matched on slug alone — which made the UI
	// claim a book was available offline in a language whose chapters were
	// never cached, a lie the reader could only discover once offline and could
	// not then fix.
	const entry = (slug: string, language: string, extra = {}) => ({
		slug,
		title: 'Humility',
		author: 'Andrew Murray',
		coverUrl: `/covers/${slug}.jpg`,
		language,
		chapterCount: 3,
		at: 100,
		...extra
	});

	it('does not report the Spanish edition as downloaded when English is', () => {
		localStorage.setItem(KEY, JSON.stringify([entry('humility', 'en')]));
		expect(offlineBooks.has('humility', 'en')).toBe(true);
		expect(offlineBooks.has('humility', 'es')).toBe(false);
	});

	it('tracks both editions of one book independently', () => {
		localStorage.setItem(
			KEY,
			JSON.stringify([entry('humility', 'en'), entry('humility', 'es', { at: 200 })])
		);
		expect(offlineBooks.list()).toHaveLength(2);
		expect(offlineBooks.has('humility', 'en')).toBe(true);
		expect(offlineBooks.has('humility', 'es')).toBe(true);
	});

	it('removing one edition leaves the other tracked', async () => {
		localStorage.setItem(
			KEY,
			JSON.stringify([entry('humility', 'en'), entry('humility', 'es', { at: 200 })])
		);
		fakeCaches([]);
		await offlineBooks.remove('humility', 'en');
		expect(offlineBooks.has('humility', 'en')).toBe(false);
		expect(offlineBooks.has('humility', 'es')).toBe(true);
		expect(offlineBooks.list()).toHaveLength(1);
	});

	it('leaves an unrelated book alone', async () => {
		localStorage.setItem(
			KEY,
			JSON.stringify([entry('humility', 'en'), entry('godliness', 'en', { at: 200 })])
		);
		fakeCaches([]);
		await offlineBooks.remove('humility', 'en');
		expect(offlineBooks.list().map((b) => b.slug)).toEqual(['godliness']);
	});

	it('deletes only the removed edition’s cached chapters', async () => {
		localStorage.setItem(
			KEY,
			JSON.stringify([entry('humility', 'en'), entry('humility', 'es', { at: 200 })])
		);
		const store = fakeCaches([
			'https://api.test/api/library/books/humility/?language=en',
			'https://api.test/api/library/books/humility/chapters/1/?language=en',
			'https://api.test/api/library/books/humility/?language=es',
			'https://api.test/api/library/books/humility/chapters/1/?language=es'
		]);

		await offlineBooks.remove('humility', 'en');

		// Matching the path alone would have taken the Spanish chapters with it,
		// leaving that edition tracked as downloaded with nothing behind it.
		expect([...store].every((u) => u.includes('language=es'))).toBe(true);
		expect(store.size).toBe(2);
	});

	it('keeps a cover the remaining edition still wears', async () => {
		// A wordless ground under /covers/art/ serves every language, so two
		// editions can share one file (see CLAUDE.md). Deleting it with the first
		// removal would blank the edition still downloaded.
		const shared = '/covers/art/humility.jpg';
		localStorage.setItem(
			KEY,
			JSON.stringify([
				entry('humility', 'en', { coverUrl: shared }),
				entry('humility', 'es', { coverUrl: shared, at: 200 })
			])
		);
		const store = fakeCaches([abs(shared)]);

		await offlineBooks.remove('humility', 'en');
		expect(store.has(abs(shared))).toBe(true);

		// Once the last edition wearing it goes, so does the file.
		await offlineBooks.remove('humility', 'es');
		expect(store.has(abs(shared))).toBe(false);
	});
});
