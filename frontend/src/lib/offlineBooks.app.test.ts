import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// This file runs the downloads as the native app's bundle sees them: no
// service worker, so a download goes to the phone's storage (the platform
// functions, stood in for here) and is read back by $lib/appOffline. The rest
// of the suite runs the website's (vitest.config.ts pins `__APP__` to false).
const p = vi.hoisted(() => ({
	files: new Map<string, string>(),
	saved: [] as { file: string; url: string }[],
	readText: vi.fn(),
	writeText: vi.fn(),
	saveFile: vi.fn(),
	del: vi.fn(),
	base: vi.fn()
}));

vi.mock('./platform', () => ({
	IS_APP: true,
	APP_ASSET_ORIGIN: 'https://ochorus.com',
	offlineReadText: p.readText,
	offlineWriteText: p.writeText,
	offlineSaveFile: p.saveFile,
	offlineDelete: p.del,
	offlineFileBase: p.base
}));

const { offlineBooks } = await import('./offlineBooks.svelte');
const { apiFetch } = await import('./api');
const { assetSrcset, assetUrl, assetHtml } = await import('./assetUrl');
const { appOfflineReady, reindexOffline } = await import('./appOffline.svelte');
const { bookApiPath, chapterApiPath } = await import('./library-public');
const { API_BASE_URL } = await import('./config');
const { apiFile } = await import('./platform/offlineFiles');
const { preloaded } = await import('../test/app-navigation');
const { readOfflineList } = await import('./offlineList');

const BASE = 'capacitor://localhost/_capacitor_file_/var/app/Library/NoCloud/offline';

const book = (language: string, extra = {}) => ({
	slug: 'humility',
	title: 'Humility',
	language,
	cover_url: '/covers/art/humility.jpg',
	author: { name: 'Andrew Murray' },
	chapters: [{ order: 1 }, { order: 2 }],
	...extra
});

/** The API as the download sees it: chapter 2 shows a picture. */
function stubApi() {
	const fetch = vi.fn(async (url: string) => {
		const path = url.slice(API_BASE_URL.length);
		if (path.includes('/chapters/2/'))
			return new Response(JSON.stringify({ body_html: '<p><img src="/illustrations/humility/plate.jpg"></p>' }));
		return new Response(JSON.stringify({ path }));
	});
	vi.stubGlobal('fetch', fetch);
	return fetch;
}

const online = (v: boolean) => Object.defineProperty(navigator, 'onLine', { value: v, configurable: true });

beforeEach(() => {
	localStorage.clear();
	reindexOffline([]);
	p.files.clear();
	p.saved.length = 0;
	preloaded.length = 0;
	p.readText.mockReset().mockImplementation(async (f: string) => p.files.get(f) ?? null);
	p.writeText.mockReset().mockImplementation(async (f: string, t: string) => (p.files.set(f, t), true));
	p.saveFile.mockReset().mockImplementation(async (file: string, url: string) => (p.saved.push({ file, url }), true));
	p.del.mockReset().mockImplementation(async (files: string[]) => {
		for (const f of files) p.files.delete(f);
	});
	p.base.mockReset().mockResolvedValue(BASE);
	online(true);
});
afterEach(() => vi.unstubAllGlobals());

describe('downloading in the app', () => {
	it('is supported with no Cache API at all', () => {
		expect('caches' in globalThis).toBe(false);
		expect(offlineBooks.supported).toBe(true);
	});

	it('stores each response under the path $lib/api requests it by', async () => {
		stubApi();
		expect(await offlineBooks.download(book('en'))).toBe(true);
		const keys = [
			bookApiPath('humility', 'en'),
			chapterApiPath('humility', 1, 'en'),
			chapterApiPath('humility', 2, 'en')
		];
		expect(keys[0]).toBe('/api/library/books/humility/?language=en');
		expect([...p.files.keys()].sort()).toEqual(keys.map(apiFile).sort());
		const [entry] = readOfflineList();
		expect(entry.apiKeys).toEqual(keys);
		expect(offlineBooks.has('humility', 'en')).toBe(true);
		// The code is bundled: nothing to preload.
		expect(preloaded).toEqual([]);
	});

	it('saves the cover, its variants and the chapters’ pictures from the website', async () => {
		stubApi();
		await offlineBooks.download(book('en'));
		const images = [
			'/covers/art/humility.jpg',
			'/covers/art/humility-320.webp',
			'/covers/art/humility-640.webp',
			'/illustrations/humility/plate.jpg'
		];
		expect(p.saved.map((s) => s.url).sort()).toEqual(images.map((i) => `https://ochorus.com${i}`).sort());
		expect(p.saved.map((s) => s.file).sort()).toEqual(images.map((i) => `img${i}`).sort());
		expect([...(readOfflineList()[0].images ?? [])].sort()).toEqual([...images].sort());
	});

	it('records only what arrived', async () => {
		stubApi();
		p.saveFile.mockImplementation(async (file: string) => !file.includes('plate'));
		p.writeText.mockImplementation(async (f: string) => !f.includes(encodeURIComponent('/chapters/2/')));
		await offlineBooks.download(book('en'));
		const [entry] = readOfflineList();
		expect(entry.images).not.toContain('/illustrations/humility/plate.jpg');
		expect(entry.apiKeys).not.toContain(chapterApiPath('humility', 2, 'en'));
		expect(entry.apiKeys).toHaveLength(2);
	});

	it('downloading again keeps what the last download stored when a piece fails this time', async () => {
		stubApi();
		await offlineBooks.download(book('en'));
		const first = readOfflineList()[0];
		p.del.mockClear();
		// A flaky network the second time: chapter 2 and the plate do not arrive.
		p.saveFile.mockImplementation(async (file: string) => !file.includes('plate'));
		p.writeText.mockImplementation(async (f: string) => !f.includes(encodeURIComponent('/chapters/2/')));
		await offlineBooks.download(book('en'));
		const [entry] = readOfflineList();
		expect(entry.apiKeys).toEqual(first.apiKeys);
		expect(entry.images).toEqual(first.images);
		expect(p.del.mock.calls.flat(2)).toEqual([]);
	});

	it('downloading again drops what the book no longer has', async () => {
		stubApi();
		await offlineBooks.download(book('en'));
		p.del.mockClear();
		await offlineBooks.download(book('en', { chapters: [{ order: 1 }] }));
		const gone = p.del.mock.calls.flat(2);
		expect(gone).toContain(apiFile(chapterApiPath('humility', 2, 'en')));
		expect(gone).toContain('img/illustrations/humility/plate.jpg');
		expect(gone).not.toContain(apiFile(chapterApiPath('humility', 1, 'en')));
		expect(readOfflineList()[0].apiKeys).toHaveLength(2);
	});

	it('removes an edition’s files but keeps the pictures another edition still shows', async () => {
		stubApi();
		await offlineBooks.download(book('en'));
		await offlineBooks.download(book('es'));
		p.del.mockClear();

		await offlineBooks.remove('humility', 'en');
		const gone = p.del.mock.calls.flat(2);
		// Its own responses…
		expect(gone).toContain(apiFile(chapterApiPath('humility', 1, 'en')));
		expect(gone.some((f: string) => f.includes('language%3Des'))).toBe(false);
		// …but not the shared ground (a wordless /covers/art/ cover serves every
		// language) nor the work's illustrations, which the Spanish edition shows.
		expect(gone.some((f: string) => f.startsWith('img/'))).toBe(false);
		expect(offlineBooks.has('humility', 'es')).toBe(true);

		p.del.mockClear();
		await offlineBooks.remove('humility', 'es');
		const last = p.del.mock.calls.flat(2);
		expect(last).toContain('img/covers/art/humility-320.webp');
		expect(last).toContain('img/illustrations/humility/plate.jpg');
		expect(p.files.size).toBe(0);
		expect(offlineBooks.list()).toEqual([]);
	});
});

describe('reading a download in the app ($lib/api)', () => {
	const key = bookApiPath('humility', 'en');

	async function downloaded() {
		stubApi();
		await offlineBooks.download(book('en'));
		p.files.set(apiFile(key), JSON.stringify({ stored: true }));
	}

	it('answers a downloaded path from the phone, then refreshes it when online', async () => {
		await downloaded();
		const fetch = stubApi();
		expect(await apiFetch(key)).toEqual({ stored: true });
		await vi.waitFor(() => expect(JSON.parse(p.files.get(apiFile(key))!)).toEqual({ path: key }));
		expect(fetch).toHaveBeenCalledTimes(1);
		expect(fetch.mock.calls[0][0]).toBe(`${API_BASE_URL}${key}`);
	});

	it('answers offline without asking the network', async () => {
		await downloaded();
		const fetch = stubApi();
		online(false);
		expect(await apiFetch(key)).toEqual({ stored: true });
		expect(fetch).not.toHaveBeenCalled();
	});

	it('asks the network for a path nobody downloaded', async () => {
		await downloaded();
		const fetch = stubApi();
		const other = bookApiPath('humility', 'fr');
		expect(await apiFetch(other)).toEqual({ path: other });
		expect(fetch).toHaveBeenCalledTimes(1);
		expect(p.readText).not.toHaveBeenCalled();
	});

	it('never answers an authenticated or non-library request', async () => {
		await downloaded();
		const fetch = stubApi();
		await apiFetch(key, { headers: { Authorization: 'Bearer t' } });
		await apiFetch('/api/auth/me/');
		await apiFetch(key, { method: 'POST', body: '{}' });
		expect(p.readText).not.toHaveBeenCalled();
		expect(fetch).toHaveBeenCalledTimes(3);
	});

	it('offline, finds an edition downloaded through the English fallback', async () => {
		// No Spanish row, so on /es the API answered in English and that is what
		// was stored; offline, the /es page's own request must reach it.
		await downloaded();
		const fetch = stubApi();
		online(false);
		const { getChapterWithLang } = await import('./library-public');
		// Answered as the API would: a 404, which the loaders fall back on…
		await expect(apiFetch(bookApiPath('humility', 'es'))).rejects.toMatchObject({ status: 404 });
		// …to the stored English, labelled English (the prose's `lang`).
		const chapter = {
			order: 1,
			title: 'I',
			body_html: '<p>x</p>',
			book_title: 'Humility',
			book_slug: 'humility',
			author_name: 'Andrew Murray'
		};
		p.files.set(apiFile(chapterApiPath('humility', 1, 'en')), JSON.stringify(chapter));
		const res = await getChapterWithLang('humility', 1, 'es');
		expect(res.language).toBe('en');
		expect(res.data.title).toBe('I');
		expect(fetch).not.toHaveBeenCalled();
	});

	it('online, a language nobody downloaded still asks the API', async () => {
		await downloaded();
		const fetch = stubApi();
		await apiFetch(bookApiPath('humility', 'es'));
		expect(fetch).toHaveBeenCalledTimes(1);
	});

	it('falls back to the network when the stored copy is missing', async () => {
		await downloaded();
		p.files.delete(apiFile(key));
		const fetch = stubApi();
		expect(await apiFetch(key)).toEqual({ path: key });
		expect(fetch).toHaveBeenCalledTimes(1);
	});
});

describe('downloaded images in the app ($lib/assetUrl)', () => {
	it('loads a saved picture from the phone, anything else from the website', async () => {
		stubApi();
		await appOfflineReady();
		expect(assetUrl('/covers/art/humility-320.webp')).toBe('https://ochorus.com/covers/art/humility-320.webp');

		await offlineBooks.download(book('en'));
		expect(assetUrl('/covers/art/humility-320.webp')).toBe(`${BASE}/img/covers/art/humility-320.webp`);
		expect(assetUrl('/covers/godliness.jpg')).toBe('https://ochorus.com/covers/godliness.jpg');
		expect(assetSrcset('/covers/art/humility-320.webp 1x, /covers/godliness-640.webp 2x')).toBe(
			`${BASE}/img/covers/art/humility-320.webp 1x, https://ochorus.com/covers/godliness-640.webp 2x`
		);
		expect(assetHtml('<img src="/illustrations/humility/plate.jpg">')).toBe(
			`<img src="${BASE}/img/illustrations/humility/plate.jpg">`
		);

		await offlineBooks.remove('humility', 'en');
		expect(assetUrl('/covers/art/humility-320.webp')).toBe('https://ochorus.com/covers/art/humility-320.webp');
	});
});
