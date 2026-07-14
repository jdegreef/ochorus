import { beforeEach, describe, expect, it } from 'vitest';
import { bookmarks } from './bookmarks.svelte';
import { BOOKMARKS_KEY } from './reading-schema';

const stored = () => JSON.parse(localStorage.getItem(BOOKMARKS_KEY) || '{}');

beforeEach(() => {
	localStorage.clear();
	bookmarks.load('inner'); // reset the reactive list to an empty book
});

describe('bookmarks store', () => {
	it('toggles a bookmark on and off at a position', () => {
		expect(bookmarks.has(2, 4)).toBe(false);

		const added = bookmarks.toggle(2, 4, 'a snippet', 'Chapter Two');
		expect(added).toBe(true);
		expect(bookmarks.has(2, 4)).toBe(true);
		expect(bookmarks.list).toHaveLength(1);

		const removed = bookmarks.toggle(2, 4, 'a snippet', 'Chapter Two');
		expect(removed).toBe(false);
		expect(bookmarks.has(2, 4)).toBe(false);
		expect(bookmarks.list).toHaveLength(0);
	});

	it('persists to localStorage and drops the book key when empty', () => {
		bookmarks.toggle(1, 0, 's', 'One');
		expect(stored().inner).toHaveLength(1);

		bookmarks.remove(bookmarks.list[0].id);
		expect(bookmarks.list).toHaveLength(0);
		// An emptied book should not linger as an empty array.
		expect('inner' in stored()).toBe(false);
	});

	it('keeps the list ordered by chapter then paragraph', () => {
		bookmarks.toggle(3, 5, 'c', 'Three');
		bookmarks.toggle(1, 9, 'a', 'One');
		bookmarks.toggle(1, 2, 'b', 'One');
		expect(bookmarks.list.map((b) => [b.order, b.p])).toEqual([
			[1, 2],
			[1, 9],
			[3, 5]
		]);
	});

	it('find/has locate by (order, p)', () => {
		bookmarks.toggle(2, 7, 'snip', 'Two');
		expect(bookmarks.find(2, 7)?.snippet).toBe('snip');
		expect(bookmarks.find(2, 8)).toBeUndefined();
	});

	it('all() gathers bookmarks across every book with their slug', () => {
		bookmarks.load('inner');
		bookmarks.toggle(1, 0, 'x', 'One');
		bookmarks.load('humility');
		bookmarks.toggle(4, 1, 'y', 'Four');

		const all = bookmarks.all();
		expect(all).toHaveLength(2);
		expect(new Set(all.map((b) => b.slug))).toEqual(new Set(['inner', 'humility']));
	});
});
