import { describe, expect, it } from 'vitest';
import { chapterPath, planDayPath, sourceHref, workPath } from './editionHref';
import { readerPrefs } from './readerPrefs.svelte';
import type { EntrySource } from './journal';

const src = (kind: EntrySource['kind'], slug: string, order = 1): EntrySource => ({
	kind,
	slug,
	order,
	p: 3,
	edition: 'en',
	title: 't',
	quote: 'q'
});

describe('sourceHref', () => {
	it('links a Notebook entry back to its passage, for every work kind', () => {
		// Each kind has its own route — a new kind must never fall through to
		// another kind's (the bug a ternary chain here invites).
		// (localizeHref settles the trailing slash; the route is what matters.)
		expect(sourceHref(src('book', 'humility', 2))).toMatch(/\/books\/humility\/2\/?\?p=3$/);
		expect(sourceHref(src('sermon', 'himself'))).toMatch(/\/sermons\/himself\/?\?p=3$/);
		expect(sourceHref(src('bio', 'andrew-murray'))).toMatch(/\/authors\/andrew-murray\/?\?p=3$/);
		expect(sourceHref(src('article', 'how-to-pray'))).toMatch(/\/articles\/how-to-pray\/?\?p=3$/);
	});
});

describe('workPath', () => {
	it('names each kind\'s page; only a book takes a chapter', () => {
		expect(workPath('book', 'humility')).toBe('/books/humility');
		expect(workPath('book', 'humility', 4)).toBe('/books/humility/4');
		expect(workPath('sermon', 'himself', 1)).toBe('/sermons/himself');
		expect(workPath('bio', 'andrew-murray')).toBe('/authors/andrew-murray');
		expect(workPath('article', 'how-to-pray')).toBe('/articles/how-to-pray/');
	});
});

describe('chapterPath (review bug #17)', () => {
	it('opens the Modern English edition only when preferred AND published', () => {
		readerPrefs.preferModern = false;
		expect(chapterPath('humility', 2, true)).toBe('/books/humility/2');
		readerPrefs.preferModern = true;
		expect(chapterPath('humility', 2, true)).toBe('/books/humility/2?edition=modern');
		// No modern edition (or not known): the original, never a Modern label on it.
		expect(chapterPath('humility', 2, false)).toBe('/books/humility/2');
		expect(chapterPath('humility', 2, undefined)).toBe('/books/humility/2');
		expect(chapterPath('humility', 2, true, 'plan=p&day=3')).toBe(
			'/books/humility/2?plan=p&day=3&edition=modern'
		);
		readerPrefs.preferModern = false;
	});
});

describe('planDayPath', () => {
	const chapterDay = { day: 3, book_slug: 'humility', chapter_order: 2, has_modern_edition: true };
	it('links a chapter day through chapterPath, with the plan context', () => {
		readerPrefs.preferModern = false;
		expect(planDayPath('p', chapterDay)).toBe('/books/humility/2?plan=p&day=3');
		// Carrying on in Modern English, as the reader's "Mark day done" does.
		expect(planDayPath('p', chapterDay, true)).toBe('/books/humility/2?plan=p&day=3&edition=modern');
	});
	it('links an article day to the article, with the plan context', () => {
		const articleDay = { day: 4, book_slug: '', chapter_order: null, article_slug: 'what-is-grace' };
		expect(planDayPath('new-to-the-faith', articleDay)).toBe(
			'/articles/what-is-grace/?plan=new-to-the-faith&day=4'
		);
	});
});

