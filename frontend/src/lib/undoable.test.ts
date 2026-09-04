import { beforeEach, describe, expect, it } from 'vitest';
import { marks } from './marks.svelte';
import { bookmarks } from './bookmarks.svelte';
import { undo } from './undo.svelte';
import { removeMarkUndoable, clearNoteUndoable, removeBookmarkUndoable } from './undoable';

beforeEach(() => {
	localStorage.clear();
	undo.dismiss();
	marks.load('humility', 1, 'en', 'book');
	bookmarks.load('book', 'humility');
});

describe('removeMarkUndoable', () => {
	it('removes the group and Undo restores its segments, note and colour', () => {
		const id = marks.add([{ p: 2, s: 4, e: 12 }, { p: 3, s: 0, e: 5 }], 'my note', 'blue');
		expect(marks.list).toHaveLength(2);

		removeMarkUndoable(id);
		expect(marks.list).toHaveLength(0);
		expect(undo.current).not.toBeNull();

		undo.act();
		expect(marks.list).toHaveLength(2);
		const restored = marks.list[0].id;
		expect(marks.getNote(restored)).toBe('my note');
		expect(marks.getColor(restored)).toBe('blue');
		expect(marks.list.map((m) => [m.p, m.s, m.e])).toEqual([[2, 4, 12], [3, 0, 5]]);
	});

	it('keeps the edition tag the mark was made with (a lossless restore)', () => {
		marks.load('humility', 1, 'es', 'book');
		const id = marks.add([{ p: 2, s: 0, e: 5 }]);
		expect(marks.list[0].lang).toBe('es');
		removeMarkUndoable(id);
		undo.act();
		expect(marks.list[0].lang).toBe('es');
	});

	it('is let go when the reader moves to another chapter, and restores nothing there', () => {
		const id = marks.add([{ p: 1, s: 0, e: 3 }]);
		removeMarkUndoable(id);
		marks.load('humility', 2, 'en', 'book'); // turned the page
		expect(undo.current).toBeNull();
		undo.act();
		expect(marks.list).toHaveLength(0); // nothing written into chapter 2
		marks.load('humility', 1, 'en', 'book');
		expect(marks.list).toHaveLength(0); // and chapter 1 stays removed
	});

	it('survives a re-load of the SAME chapter (the drawer re-loads on every open)', () => {
		const id = marks.add([{ p: 1, s: 0, e: 3 }]);
		removeMarkUndoable(id);
		marks.load('humility', 1, 'en', 'book');
		expect(undo.current).not.toBeNull();
	});

	it('does not double-add segments the reader re-highlighted before Undo', () => {
		const id = marks.add([{ p: 4, s: 0, e: 9 }], 'kept');
		removeMarkUndoable(id);
		marks.add([{ p: 4, s: 0, e: 9 }]); // pen again, same range
		undo.act();
		expect(marks.list).toHaveLength(1);
	});

	it('offers nothing for an unknown id', () => {
		removeMarkUndoable('nope');
		expect(undo.current).toBeNull();
	});
});

describe('clearNoteUndoable', () => {
	it('clears the note and Undo puts the text back', () => {
		const id = marks.add([{ p: 0, s: 0, e: 4 }], 'keep me');
		clearNoteUndoable(id);
		expect(marks.getNote(id)).toBe('');
		undo.act();
		expect(marks.getNote(id)).toBe('keep me');
	});

	it('offers nothing when there was no note to lose', () => {
		const id = marks.add([{ p: 0, s: 0, e: 4 }]);
		clearNoteUndoable(id);
		expect(undo.current).toBeNull();
	});
});

describe('removeBookmarkUndoable', () => {
	it('removes the bookmark and Undo re-saves the spot', () => {
		bookmarks.toggle(3, 7, 'a snippet', 'Three');
		const id = bookmarks.list[0].id;
		removeBookmarkUndoable(id);
		expect(bookmarks.has(3, 7)).toBe(false);
		undo.act();
		expect(bookmarks.has(3, 7)).toBe(true);
		expect(bookmarks.find(3, 7)?.snippet).toBe('a snippet');
	});

	it('does not double-add if the spot was re-bookmarked before Undo', () => {
		bookmarks.toggle(3, 7, 's', 'T');
		removeBookmarkUndoable(bookmarks.list[0].id);
		bookmarks.toggle(3, 7, 's', 'T'); // reader re-saved it themselves
		undo.act();
		expect(bookmarks.list.filter((b) => b.order === 3 && b.p === 7)).toHaveLength(1);
	});
});
