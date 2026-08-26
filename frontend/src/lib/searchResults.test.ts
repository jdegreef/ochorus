import { describe, expect, it } from 'vitest';
import {
	GROUP_ORDER,
	grandTotal,
	groupRows,
	navList,
	passageBooks,
	toRow,
	totalFor,
	type ResultRow
} from './searchResults';
import type { SearchHit } from './library-public';

const ctx = { label: (t: string) => `[${t}]`, query: 'prayer' };

const author = (slug = 'andrew-murray') =>
	({
		type: 'author',
		author_slug: slug,
		author_name: 'Andrew Murray',
		snippet: 'a life of prayer',
		date: '1900',
		photo_url: `/p/${slug}.webp`
	}) as unknown as SearchHit;

const book = (slug = 'humility') =>
	({
		type: 'book',
		book_slug: slug,
		book_title: 'Humility',
		author_name: 'Andrew Murray',
		snippet: '',
		date: '1895',
		cover_url: `/c/${slug}.webp`,
		cover_color: '#123456'
	}) as unknown as SearchHit;

const chapter = (bookSlug: string, order: number, title = '') =>
	({
		type: 'chapter',
		book_slug: bookSlug,
		book_title: 'Humility',
		author_name: 'Andrew Murray',
		chapter_order: order,
		chapter_title: title,
		snippet: 'the spirit of prayer',
		date: '1895',
		cover_url: '/c/humility.webp',
		cover_color: '#123456'
	}) as unknown as SearchHit;

const sermon = (slug = 'himself', ref = '') =>
	({
		type: 'sermon',
		sermon_slug: slug,
		sermon_title: 'Himself',
		author_name: 'A. B. Simpson',
		scripture_ref: ref,
		snippet: '',
		date: '1890'
	}) as unknown as SearchHit;

const rowsOf = (hits: SearchHit[]): ResultRow[] =>
	hits.map((h) => ({ ...toRow(h, ctx), type: h.type }));

describe('toRow', () => {
	// The query rides along so the reader lands on the match rather than at the
	// top of a chapter — the whole point of arriving from a search.
	it('carries the query into chapter and sermon links, and nowhere else', () => {
		expect(toRow(chapter('humility', 3), ctx).href).toBe('/books/humility/3?q=prayer');
		expect(toRow(sermon(), ctx).href).toBe('/sermons/himself?q=prayer');
		expect(toRow(book(), ctx).href).toBe('/books/humility');
		expect(toRow(author(), ctx).href).toBe('/authors/andrew-murray');
	});

	it('escapes a query that would otherwise break the URL', () => {
		const href = toRow(chapter('humility', 3), { ...ctx, query: 'faith & hope' }).href;
		expect(href).toBe('/books/humility/3?q=faith%20%26%20hope');
	});

	it('omits the parameter entirely when there is no query', () => {
		expect(toRow(chapter('humility', 3), { ...ctx, query: '' }).href).toBe('/books/humility/3');
	});

	it('gives every type a key unique across types', () => {
		const keys = rowsOf([author(), book(), chapter('humility', 1), sermon()]).map((r) => r.key);
		expect(new Set(keys).size).toBe(keys.length);
	});

	// A chapter with no title of its own falls back to the book's, or the row
	// renders as an untitled line the reader can't identify.
	it('falls back to the book title for an untitled chapter', () => {
		expect(toRow(chapter('humility', 2), ctx).title).toBe('Humility');
		expect(toRow(chapter('humility', 2, 'The Path'), ctx).title).toBe('The Path');
	});

	it('appends a scripture reference to a sermon only when there is one', () => {
		expect(toRow(sermon('himself', 'John 3:16'), ctx).meta).toBe('A. B. Simpson · John 3:16');
		expect(toRow(sermon('himself'), ctx).meta).toBe('A. B. Simpson');
	});

	// Portraits are round and cropped to the face; covers keep their proportions.
	it('marks portraits round and covers not', () => {
		expect(toRow(author(), ctx).round).toBe(true);
		expect(toRow(author(), ctx).focus).toBeTruthy();
		expect(toRow(book(), ctx).round).toBe(false);
		expect(toRow(book(), ctx).focus).toBeUndefined();
	});
});

describe('groupRows', () => {
	it('orders sections editorially, not by arrival', () => {
		// Hits arrive passages-first; the reader wants the book and the author.
		const groups = groupRows(rowsOf([chapter('humility', 1), author(), book()]));
		expect(groups.map((g) => g.type)).toEqual(['book', 'author', 'chapter']);
	});

	it('keeps only the sections present', () => {
		expect(groupRows(rowsOf([book()])).map((g) => g.type)).toEqual(['book']);
		expect(groupRows([])).toEqual([]);
	});

	it('covers every hit type', () => {
		const types = rowsOf([author(), book(), chapter('humility', 1), sermon()]).map((r) => r.type);
		for (const t of types) {
			expect(GROUP_ORDER.some((g) => g.type === t)).toBe(true);
		}
	});
});

describe('passageBooks', () => {
	it('clusters chapters under their book in server order', () => {
		const books = passageBooks([
			chapter('humility', 5),
			chapter('waiting-on-god', 1),
			chapter('humility', 2)
		]);
		expect(books.map((b) => b.slug)).toEqual(['humility', 'waiting-on-god']);
		// Book order preserved: 5 came first because the server ranked it first.
		expect(books[0].chapters.map((c) => c.order)).toEqual([5, 2]);
	});

	it('ignores hits that are not passages', () => {
		expect(passageBooks([author(), book(), sermon()])).toEqual([]);
	});
});

describe('counting', () => {
	// The bug this exists for: the page reported the rows it held, so a search
	// matching four hundred passages rendered "30 results".
	it('reports the server total, not the number of rows loaded', () => {
		const groups = groupRows(rowsOf([book(), chapter('humility', 1)]));
		expect(grandTotal(groups, { book: 4, chapter: 400 })).toBe(404);
	});

	it('falls back to what is loaded for a type the server did not count', () => {
		const groups = groupRows(rowsOf([book('a'), book('b')]));
		// An undercount, never an invented number.
		expect(grandTotal(groups, {})).toBe(2);
	});

	it('totalFor prefers the server count over the loaded length', () => {
		expect(totalFor({ chapter: 400 }, 'chapter', 30)).toBe(400);
		expect(totalFor({}, 'chapter', 30)).toBe(30);
	});
});

describe('navList', () => {
	const groups = groupRows(rowsOf([book(), chapter('humility', 1), chapter('humility', 2)]));
	const books = passageBooks([chapter('humility', 1), chapter('humility', 2)]);

	it('walks the sections in display order', () => {
		const nav = navList(groups, books, new Set(), 3);
		expect(nav.keys[0]).toBe('book:humility');
		expect(nav.keys.slice(1)).toEqual(['humility:1', 'humility:2']);
	});

	// A collapsed book contributes its preview and no more, or the arrow keys
	// walk rows the reader cannot see.
	it('stops at the preview cap for a collapsed book', () => {
		const many = passageBooks([1, 2, 3, 4, 5].map((n) => chapter('humility', n)));
		const g = groupRows(rowsOf([1, 2, 3, 4, 5].map((n) => chapter('humility', n))));
		expect(navList(g, many, new Set(), 3).keys).toHaveLength(3);
		expect(navList(g, many, new Set(['humility']), 3).keys).toHaveLength(5);
	});

	it('maps every key to a destination, a label and its type', () => {
		const nav = navList(groups, books, new Set(), 3);
		for (const k of nav.keys) {
			expect(nav.map.get(k)).toBeTruthy();
			expect(nav.labels.get(k)).toBeTruthy();
			expect(nav.types.get(k)).toBeTruthy();
		}
		expect(nav.map.get('humility:2')).toBe('/books/humility/2');
		expect(nav.types.get('humility:2')).toBe('chapter');
	});
});
