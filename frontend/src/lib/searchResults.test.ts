import { describe, expect, it } from 'vitest';
import {
	GROUP_ORDER,
	grandTotal,
	groupRows,
	leadWithPinned,
	navList,
	toRow,
	topResult,
	totalFor,
	type ResultGroup,
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

const article = (slug = 'how-to-forgive') =>
	({
		type: 'article',
		article_slug: slug,
		article_title: 'How to Forgive',
		snippet: 'a short guide to prayer',
		date: '2026'
	}) as unknown as SearchHit;

const scripture = (chapter = 8, verse: number | null = 28) =>
	({
		type: 'scripture',
		book_slug: 'romans',
		chapter,
		verse,
		reference: verse ? `Romans ${chapter}:${verse}` : `Romans ${chapter}`,
		snippet: '',
		date: ''
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
		// An article is a hub, not a passage, so its link carries no ?q= anchor.
		expect(toRow(article('how-to-forgive'), ctx).href).toBe('/articles/how-to-forgive');
		// A verse page and a whole-chapter page differ by the trailing segment.
		expect(toRow(scripture(8, 28), ctx).href).toBe('/scripture/romans/8/28/');
		expect(toRow(scripture(8, null), ctx).href).toBe('/scripture/romans/8/');
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

	// A chapter with no title of its own is NAMED by its number, not by the
	// book's title. Falling back to the book collapsed every hit from an
	// untitled book into identical rows — Purpose in Prayer is thirteen
	// untitled chapters, so a search across it returned thirteen lines all
	// reading "Purpose in Prayer". The book is still on the row, in `meta`.
	it('names an untitled chapter by its number', () => {
		expect(toRow(chapter('humility', 2), ctx).title).toBe('Chapter 2');
		expect(toRow(chapter('humility', 2), ctx).meta).toContain('Humility');
		expect(toRow(chapter('humility', 2, 'The Path'), ctx).title).toBe('The Path');
	});

	it('appends a scripture reference to a sermon only when there is one', () => {
		expect(toRow(sermon('himself', 'John 3:16'), ctx).meta).toBe('A. B. Simpson · John 3:16');
		expect(toRow(sermon('himself'), ctx).meta).toBe('A. B. Simpson');
	});

	it('draws a sermon as its passage monogram in its shelf hue', () => {
		const row = toRow(sermon('himself', 'John 3:16'), ctx);
		expect(row.monogram).toEqual({ scriptureRef: 'John 3:16', title: 'Himself' });
		expect(row.color).toMatch(/^#[0-9a-f]{6}$/i);
		expect(row.round).toBe(true);
		expect(toRow(book(), ctx).monogram).toBeUndefined();
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
		const types = rowsOf([
			author(),
			book(),
			chapter('humility', 1),
			sermon(),
			article(),
			scripture()
		]).map((r) => r.type);
		for (const t of types) {
			expect(GROUP_ORDER.some((g) => g.type === t)).toBe(true);
		}
	});

	it('leads with the scripture passage hub, above the works that treat it', () => {
		const groups = groupRows(rowsOf([book(), chapter('humility', 1), scripture()]));
		expect(groups.map((g) => g.type)).toEqual(['scripture', 'book', 'chapter']);
	});

	it('files articles among the navigational entities, before passages', () => {
		const groups = groupRows(rowsOf([chapter('humility', 1), article(), book()]));
		expect(groups.map((g) => g.type)).toEqual(['book', 'article', 'chapter']);
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

	it('walks the sections in display order', () => {
		const nav = navList(groups);
		expect(nav.keys).toEqual(['book:humility', 'chapter:humility:1', 'chapter:humility:2']);
	});

	it('maps every key to a destination, a label and its type', () => {
		const nav = navList(groups);
		for (const k of nav.keys) {
			expect(nav.map.get(k)).toBeTruthy();
			expect(nav.labels.get(k)).toBeTruthy();
			expect(nav.types.get(k)).toBeTruthy();
		}
		expect(nav.map.get('chapter:humility:2')).toBe('/books/humility/2?q=prayer');
		expect(nav.types.get('chapter:humility:2')).toBe('chapter');
	});
});

describe('passage location', () => {
	it('names a passage by its book and chapter', () => {
		expect(toRow(chapter('humility', 3, 'Humility and Faith'), ctx).location).toBe(
			'Humility · Humility and Faith'
		);
	});

	it('is carried by passages only', () => {
		expect(toRow(book(), ctx).location).toBeUndefined();
		expect(toRow(sermon(), ctx).location).toBeUndefined();
	});
});

describe('topResult', () => {
	it('promotes a book the query names exactly, ignoring case, accents and punctuation', () => {
		const other = { ...(book('absolute-surrender') as object), book_title: 'Absolute Surrender' } as SearchHit;
		const rows = rowsOf([other, book()]);
		expect(topResult(rows, 'humility')?.key).toBe('book:humility');
		expect(topResult(rows, '  HUMILITY! ')?.key).toBe('book:humility');
		expect(topResult(rowsOf([author()]), 'andrew murráy')?.key).toBe('author:andrew-murray');
	});

	it('promotes nothing for a partial match or a passage', () => {
		expect(topResult(rowsOf([book()]), 'humil')).toBeNull();
		expect(topResult(rowsOf([chapter('x', 1, 'Prayer')]), 'prayer')).toBeNull();
		expect(topResult(rowsOf([book()]), 'h')).toBeNull();
	});

	it('prefers the book when a book and a writer share the name', () => {
		const same = { ...(author() as object), author_name: 'Humility' } as SearchHit;
		expect(topResult(rowsOf([same, book()]), 'humility')?.type).toBe('book');
	});

	it('leads with an admin-pinned book or writer even when it is not an exact match', () => {
		const rows = rowsOf([book()]).map((r) => ({ ...r, pinned: true }));
		expect(topResult(rows, 'meekness')?.key).toBe('book:humility');
	});
});

describe('cover faces', () => {
	const face = {
		slug: 'rooted-1',
		language: 'en',
		title: 'Rooted',
		subtitle: '',
		cover_title: '',
		cover_url: '/covers/rooted-1.svg',
		cover_color: '#2f5d3a',
		series_position: 1,
		author: { slug: 'ochorus', name: 'Ochorus', birth_year: null }
	};

	it('carries a book or chapter hit’s cover so the thumbnail can draw it', () => {
		const withFace = (h: SearchHit) => ({ ...h, cover: face }) as SearchHit;
		expect(toRow(withFace(book('rooted-1')), ctx).face).toEqual(face);
		expect(toRow(withFace(chapter('rooted-1', 2)), ctx).face).toEqual(face);
	});

	it('leaves it out from an API behind this build, so the bare image still shows', () => {
		const row = toRow(book(), ctx);
		expect(row.face).toBeUndefined();
		expect(row.image).toBe('/c/humility.webp');
	});
});

describe('leadWithPinned', () => {
	const row = (type: ResultRow['type'], pinned = false) =>
		({ type, pinned, key: `${type}-${pinned}`, href: '', title: type }) as unknown as ResultRow;
	const group = (type: ResultRow['type'], rows: ResultRow[]): ResultGroup => ({
		type,
		labelKey: type,
		rows
	});

	it('moves the group holding a pinned best match to the front', () => {
		const groups = [
			group('book', [row('book')]),
			group('author', [row('author')]),
			group('topic', [row('topic', true)])
		];
		expect(leadWithPinned(groups).map((g) => g.type)).toEqual(['topic', 'book', 'author']);
	});

	it('leaves the order alone when nothing is pinned or the pin already leads', () => {
		const groups = [group('book', [row('book', true)]), group('topic', [row('topic')])];
		expect(leadWithPinned(groups)).toBe(groups);
		const plain = [group('book', [row('book')])];
		expect(leadWithPinned(plain)).toBe(plain);
	});
});
