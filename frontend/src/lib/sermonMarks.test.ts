import { beforeEach, describe, expect, it } from 'vitest';
import { marks } from './marks.svelte';
import {
	MARKS_KEY,
	ANCHOR_KEY,
	LEGACY_SERMON_MARKS_KEY,
	LEGACY_SERMON_ANCHOR_KEY,
	SERMON_CHAPTER_ORDER
} from './reading-schema';
import { getScrollAnchor } from './progress';

beforeEach(() => localStorage.clear());

describe('sermon marks via the unified store (kind="sermon")', () => {
	it('adds a selection as one group, toggles and removes it', () => {
		marks.load('faith', SERMON_CHAPTER_ORDER, 'en', 'sermon');
		const id = marks.add([
			{ p: 0, s: 0, e: 5 },
			{ p: 1, s: 0, e: 3 }
		]);
		expect(id).toBeTruthy();
		expect(marks.list).toHaveLength(2);
		expect(marks.groupCovering([{ p: 0, s: 0, e: 5 }, { p: 1, s: 0, e: 3 }])).toBe(id);

		marks.remove(id);
		expect(marks.list).toHaveLength(0);
	});

	it('keeps a sermon and a book with the same slug apart', () => {
		marks.load('free-grace', 1, 'en', 'book');
		marks.add([{ p: 0, s: 0, e: 2 }]);
		marks.load('free-grace', SERMON_CHAPTER_ORDER, 'en', 'sermon');
		expect(marks.list).toHaveLength(0); // the book's mark doesn't bleed over
		marks.add([{ p: 3, s: 0, e: 4 }]);

		const all = marks.all();
		expect(new Set(all.map((m) => `${m.kind}:${m.slug}`))).toEqual(
			new Set(['book:free-grace', 'sermon:free-grace'])
		);
	});

	it('scopes marks per sermon slug and persists across loads', () => {
		marks.load('a', SERMON_CHAPTER_ORDER, 'en', 'sermon');
		marks.add([{ p: 0, s: 0, e: 2 }]);
		marks.load('b', SERMON_CHAPTER_ORDER, 'en', 'sermon');
		expect(marks.list).toHaveLength(0); // b has none
		marks.load('a', SERMON_CHAPTER_ORDER, 'en', 'sermon');
		expect(marks.list).toHaveLength(1); // a's mark survived
	});

	it('migrates the legacy device-local sermon stores once', () => {
		localStorage.setItem(
			LEGACY_SERMON_MARKS_KEY,
			JSON.stringify({ faith: [{ id: 'x', p: 2, s: 0, e: 5 }] })
		);
		localStorage.setItem(LEGACY_SERMON_ANCHOR_KEY, JSON.stringify({ faith: 7 }));

		marks.load('faith', SERMON_CHAPTER_ORDER, 'en', 'sermon');
		expect(marks.list).toHaveLength(1);
		expect(marks.list[0].p).toBe(2);
		expect(localStorage.getItem(LEGACY_SERMON_MARKS_KEY)).toBeNull();

		expect(getScrollAnchor('faith', SERMON_CHAPTER_ORDER, 'sermon')).toBe(7);
		expect(localStorage.getItem(LEGACY_SERMON_ANCHOR_KEY)).toBeNull();

		// Folded into the unified keys, not lost.
		expect(JSON.parse(localStorage.getItem(MARKS_KEY)!)['sermon:faith:1']).toBeTruthy();
		expect(JSON.parse(localStorage.getItem(ANCHOR_KEY)!)['sermon:faith:1']).toBe(7);
	});
});
