import { beforeEach, describe, it, expect } from 'vitest';
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
});
