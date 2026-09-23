import { beforeEach, describe, expect, it, vi } from 'vitest';
import { bookmarks } from './bookmarks.svelte';
import { readingSync } from './readingSync';
import { BOOKMARKS_KEY, SERMON_CHAPTER_ORDER } from './reading-schema';
import { bookmarkTarget, pendingAt } from './removals';

const stored = () => JSON.parse(localStorage.getItem(BOOKMARKS_KEY) || '{}');

beforeEach(() => {
	localStorage.clear();
	bookmarks.load('book', 'inner'); // reset the reactive list to an empty work
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

	it('mirrors add and remove to the account via readingSync', () => {
		const push = vi.spyOn(readingSync, 'pushBookmark');
		const remove = vi.spyOn(readingSync, 'removeBookmark');
		try {
			bookmarks.toggle(2, 4, 'a snippet', 'Chapter Two');
			expect(push).toHaveBeenCalledTimes(1);
			expect(push.mock.calls[0].slice(0, 2)).toEqual(['book', 'inner']);
			expect(push.mock.calls[0][2]).toMatchObject({ order: 2, p: 4 });

			bookmarks.toggle(2, 4, 'a snippet', 'Chapter Two'); // toggles off
			expect(remove).toHaveBeenCalledWith('book', 'inner', 2, 4);
		} finally {
			push.mockRestore();
			remove.mockRestore();
		}
	});

	it('persists to localStorage and drops the work key when empty', () => {
		bookmarks.toggle(1, 0, 's', 'One');
		expect(stored().inner).toHaveLength(1);

		bookmarks.remove(bookmarks.list[0].id);
		expect(bookmarks.list).toHaveLength(0);
		// An emptied work should not linger as an empty array.
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

	it('all() gathers bookmarks across every work with its kind and slug', () => {
		bookmarks.load('book', 'inner');
		bookmarks.toggle(1, 0, 'x', 'One');
		bookmarks.load('book', 'humility');
		bookmarks.toggle(4, 1, 'y', 'Four');

		const all = bookmarks.all();
		expect(all).toHaveLength(2);
		expect(new Set(all.map((b) => b.slug))).toEqual(new Set(['inner', 'humility']));
		expect(new Set(all.map((b) => b.kind))).toEqual(new Set(['book']));
	});
});

describe('the three long-form kinds', () => {
	it('bookmarks a sermon', () => {
		bookmarks.load('sermon', 'possibilities');
		expect(bookmarks.toggle(SERMON_CHAPTER_ORDER, 12, 'a line', 'Possibilities')).toBe(true);

		bookmarks.load('sermon', 'possibilities');
		expect(bookmarks.has(SERMON_CHAPTER_ORDER, 12)).toBe(true);
	});

	it('bookmarks a biography', () => {
		bookmarks.load('bio', 'a-b-simpson');
		bookmarks.toggle(1, 3, 'his life', 'A. B. Simpson');

		const all = bookmarks.all();
		expect(all).toHaveLength(1);
		expect(all[0].kind).toBe('bio');
		expect(all[0].slug).toBe('a-b-simpson');
	});

	it('keeps a book and a sermon of the same slug apart', () => {
		// The reason the key is prefixed at all. `humility` is a real book slug,
		// and nothing stops a sermon from carrying one too — under a bare slug
		// they shared a list, so bookmarking the sermon lit up the book and the
		// notebook filed both under whichever it looked up first.
		bookmarks.load('book', 'humility');
		bookmarks.toggle(1, 0, 'from the book', 'Chapter One');

		bookmarks.load('sermon', 'humility');
		expect(bookmarks.has(1, 0), 'the sermon must not inherit the book').toBe(false);
		bookmarks.toggle(1, 0, 'from the sermon', 'Humility');

		bookmarks.load('book', 'humility');
		expect(bookmarks.list).toHaveLength(1);
		expect(bookmarks.list[0].snippet).toBe('from the book');

		const all = bookmarks.all();
		expect(all).toHaveLength(2);
		expect(new Set(all.map((b) => b.kind))).toEqual(new Set(['book', 'sermon']));
	});

	it('leaves book bookmarks saved before this change exactly where they were', () => {
		// Books stay under the bare slug for precisely this reason: a prefix for
		// all three kinds would have orphaned every bookmark already on a device.
		localStorage.setItem(
			BOOKMARKS_KEY,
			JSON.stringify({
				inner: [{ id: 'old', order: 2, p: 5, snippet: 'saved long ago', title: 'Two', at: 1 }]
			})
		);
		bookmarks.load('book', 'inner');
		expect(bookmarks.list).toHaveLength(1);
		expect(bookmarks.list[0].snippet).toBe('saved long ago');
		expect(bookmarks.all()[0].kind).toBe('book');
	});
});

describe('un-bookmarking is remembered until the account confirms it', () => {
	it('records a pending removal for that spot, and re-saving lifts it', () => {
		bookmarks.toggle(2, 4, 's', 't');
		bookmarks.toggle(2, 4, 's', 't');
		expect(pendingAt('bookmark', 'book', bookmarkTarget('inner', 2, 4))).toBeTypeOf('number');
		expect(pendingAt('bookmark', 'book', bookmarkTarget('inner', 2, 5))).toBeNull();
		bookmarks.toggle(2, 4, 's', 't');
		expect(pendingAt('bookmark', 'book', bookmarkTarget('inner', 2, 4))).toBeNull();
	});
});
