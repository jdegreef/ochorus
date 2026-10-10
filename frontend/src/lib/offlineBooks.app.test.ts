import { afterEach, describe, expect, it, vi } from 'vitest';

// This file runs offlineBooks as the native app's bundle sees it. The rest of
// the suite runs the website's (vitest.config.ts pins `__APP__` to false).
vi.mock('./platform', () => ({ IS_APP: true }));

const { offlineBooks } = await import('./offlineBooks.svelte');

afterEach(() => vi.unstubAllGlobals());

describe('offlineBooks in the native app', () => {
	it('is unsupported even where the Cache API exists — no service worker would serve it', () => {
		vi.stubGlobal('caches', { open: vi.fn() });
		expect(offlineBooks.supported).toBe(false);
	});

	it('refuses a download without fetching or caching anything', async () => {
		const open = vi.fn();
		const fetch = vi.fn();
		vi.stubGlobal('caches', { open });
		vi.stubGlobal('fetch', fetch);
		const book = {
			slug: 'godliness',
			title: 'Godliness',
			language: 'en',
			cover_url: '',
			author: { name: 'Catherine Booth' },
			chapters: [{ order: 1 }]
		};
		expect(await offlineBooks.download(book)).toBe(false);
		expect(open).not.toHaveBeenCalled();
		expect(fetch).not.toHaveBeenCalled();
		expect(offlineBooks.active).toBeNull();
	});
});
