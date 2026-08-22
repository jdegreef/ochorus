import { beforeEach, describe, it, expect } from 'vitest';
import { coverVariants } from './coverArt';
import { offlineBooks } from './offlineBooks.svelte';

const KEY = 'ochorus:offline-books';

beforeEach(() => localStorage.clear());

describe('offlineBooks tracking', () => {
	it('is empty on a fresh device', () => {
		expect(offlineBooks.list()).toEqual([]);
		expect(offlineBooks.has('godliness')).toBe(false);
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
		expect(offlineBooks.has('a')).toBe(true);
		expect(offlineBooks.has('c')).toBe(false);
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
		expect(offlineBooks.has('godliness')).toBe(false);
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
