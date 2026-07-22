import { beforeEach, describe, it, expect } from 'vitest';
import { readingCounts } from './readingStats';
import { PROGRESS_KEY, MARKS_KEY, FAVORITES_KEY, BOOKMARKS_KEY } from './reading-schema';

beforeEach(() => localStorage.clear());

describe('readingCounts', () => {
	it('is all zeros on a fresh device', () => {
		expect(readingCounts()).toEqual({
			inProgress: 0,
			highlights: 0,
			notes: 0,
			favorites: 0,
			bookmarks: 0
		});
	});

	it('counts progress, highlights, notes, favorites and bookmarks', () => {
		localStorage.setItem(
			PROGRESS_KEY,
			JSON.stringify({
				humility: { order: 3, paragraph_index: 0, language: 'en', at: 1 },
				'sermon:free-grace': { order: 1, paragraph_index: 0, language: 'en', at: 2 }
			})
		);
		localStorage.setItem(
			MARKS_KEY,
			JSON.stringify({
				'humility:3': {
					m: [
						{ id: 'a', p: 1, s: 0, e: 5 },
						{ id: 'b', p: 2, s: 0, e: 5, note: 'convicting' }
					]
				}
			})
		);
		localStorage.setItem(
			FAVORITES_KEY,
			JSON.stringify({ 'book:humility': 1, 'author:andrew-murray': 2 })
		);
		localStorage.setItem(
			BOOKMARKS_KEY,
			JSON.stringify({ humility: [{ id: 'x', order: 2, p: 0, snippet: 's', title: 't', at: 1 }] })
		);
		expect(readingCounts()).toEqual({
			inProgress: 2,
			highlights: 2,
			notes: 1,
			favorites: 2,
			bookmarks: 1
		});
	});
});
