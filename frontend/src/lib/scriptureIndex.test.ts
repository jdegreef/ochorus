import { describe, it, expect } from 'vitest';
import type { ScripturePageEntry } from '$lib/library-public';
import {
	BIBLE_SECTIONS,
	bookFromPageList,
	groupScripture,
	heatScale,
	mayBeReference,
	relativeHeat,
	mostCited,
	TOP_VERSES_PER_BOOK
} from './scriptureIndex';

const page = (
	book: string,
	order: number,
	chapter: number,
	count: number,
	verse: number | null = null
): ScripturePageEntry => ({
	book,
	book_title: book[0].toUpperCase() + book.slice(1),
	book_order: order,
	chapter,
	verse,
	citing_count: count
});

describe('BIBLE_SECTIONS', () => {
	it('covers books 1–66 once each, in order', () => {
		const seen: number[] = [];
		for (const s of BIBLE_SECTIONS) for (let o = s.from; o <= s.to; o++) seen.push(o);
		expect(seen).toEqual(Array.from({ length: 66 }, (_, i) => i + 1));
	});
	it('splits the testaments at Matthew', () => {
		expect(BIBLE_SECTIONS.filter((s) => s.testament === 'old').at(-1)!.to).toBe(39);
		expect(BIBLE_SECTIONS.find((s) => s.testament === 'new')!.from).toBe(40);
	});
});

describe('groupScripture', () => {
	it('groups books into their sections in canonical order, dropping empty sections', () => {
		const out = groupScripture([
			page('romans', 45, 8, 30),
			page('genesis', 1, 3, 5),
			page('exodus', 2, 20, 4),
			page('psalms', 19, 23, 9)
		]);
		expect(out.map((s) => s.key)).toEqual(['law', 'wisdom', 'paul']);
		expect(out[0].books.map((b) => b.slug)).toEqual(['genesis', 'exodus']);
	});

	it('sorts chapters and keeps verse pages out of the chapter row', () => {
		const [law] = groupScripture([page('genesis', 1, 22, 5), page('genesis', 1, 3, 5), page('genesis', 1, 3, 4, 15)]);
		expect(law.books[0].chapters).toEqual([
			{ chapter: 3, count: 5 },
			{ chapter: 22, count: 5 }
		]);
	});

	it('surfaces the most-cited verse pages, ties in Bible order, capped', () => {
		const verses = [
			page('romans', 45, 8, 9, 28),
			page('romans', 45, 5, 4, 8),
			page('romans', 45, 8, 4, 1),
			page('romans', 45, 12, 2, 1),
			page('romans', 45, 3, 3, 23),
			page('romans', 45, 6, 3, 23),
			page('romans', 45, 1, 2, 16)
		];
		const [paul] = groupScripture([page('romans', 45, 8, 30), ...verses]);
		const top = paul.books[0].topVerses;
		expect(top).toHaveLength(TOP_VERSES_PER_BOOK);
		expect(top.map((v) => `${v.chapter}:${v.verse}`)).toEqual(['8:28', '5:8', '8:1', '3:23', '6:23']);
	});

	it('keeps a book outside the 66 in a trailing section', () => {
		const out = groupScripture([page('tobit', 67, 4, 3), page('genesis', 1, 1, 3)]);
		expect(out.map((s) => s.key)).toEqual(['law', 'other']);
	});

	it('skips a book that has verse pages but no chapter page', () => {
		expect(groupScripture([page('jude', 65, 1, 3, 24)])).toEqual([]);
	});
});

describe('heatScale', () => {
	it('puts the bottom half at 0 and the very top at the highest level', () => {
		const counts = Array.from({ length: 100 }, (_, i) => i + 1);
		const level = heatScale(counts);
		expect(level(1)).toBe(0);
		expect(level(50)).toBe(0);
		expect(level(51)).toBe(1);
		expect(level(76)).toBe(2);
		expect(level(91)).toBe(3);
		expect(level(100)).toBe(4);
	});
	it('gives equal counts the same level, and a flat library no heat', () => {
		const level = heatScale([3, 3, 3, 3]);
		expect(level(3)).toBe(0);
	});
	it('is never above the top level or below 0', () => {
		const level = heatScale([1, 2, 2, 2, 2, 9]);
		for (const c of [0, 1, 2, 9, 50]) {
			expect(level(c)).toBeGreaterThanOrEqual(0);
			expect(level(c)).toBeLessThanOrEqual(4);
		}
	});
	it('climbs one level per step on a long tail, keeping the top level to the top 3%', () => {
		// 60 chapters cited once, 20 twice, 10 three times, 7 five times, then 20, 40, 90.
		const counts = [
			...Array(60).fill(1),
			...Array(20).fill(2),
			...Array(10).fill(3),
			...Array(7).fill(5),
			20,
			40,
			90
		];
		const level = heatScale(counts);
		expect([1, 2, 3, 5, 20, 40, 90].map(level)).toEqual([0, 1, 2, 3, 4, 4, 4]);
		expect(counts.filter((c) => level(c) === 4)).toHaveLength(3);
	});
	it('does not hand the top level to everything above the minimum', () => {
		// 80 chapters cited once, 20 twice: the twice-cited are the top 20%, not the top 3%.
		const level = heatScale([...Array(80).fill(1), ...Array(20).fill(2)]);
		expect(level(1)).toBe(0);
		expect(level(2)).toBe(2);
	});
	it('copes with no counts', () => {
		expect(heatScale([])(10)).toBe(0);
	});
});

describe('mostCited', () => {
	it('ranks chapter pages only, ties in Bible order', () => {
		const top = mostCited(
			[page('john', 43, 3, 40), page('romans', 45, 8, 40), page('romans', 45, 8, 99, 28), page('genesis', 1, 3, 12)],
			2
		);
		expect(top.map((t) => `${t.slug} ${t.chapter}`)).toEqual(['john 3', 'romans 8']);
	});
});

describe('mayBeReference', () => {
	it('asks the resolver only when a chapter number is present', () => {
		for (const q of ['Rom 8:28', 'Ps 23', '1 Cor 13', 'john 3']) expect(mayBeReference(q)).toBe(true);
		for (const q of ['grace', 'John Bunyan', 'Romans']) expect(mayBeReference(q)).toBe(false);
	});
});

describe('relativeHeat', () => {
	it("makes the book's most-cited chapter the brightest, the rest in proportion", () => {
		const level = relativeHeat([4, 8, 16, 40]);
		expect([4, 8, 16, 40].map(level)).toEqual([0, 1, 2, 4]);
	});
	it('gives a single-chapter book the top shade, and no counts no heat', () => {
		expect(relativeHeat([7])(7)).toBe(4);
		expect(relativeHeat([])(3)).toBe(0);
	});
});

describe('bookFromPageList', () => {
	const list = [
		page('genesis', 1, 3, 9),
		page('romans', 45, 8, 30),
		page('romans', 45, 5, 6),
		page('romans', 45, 8, 12, 28),
		page('john', 43, 3, 20)
	];
	it('builds the book page from the list, leaving server-only counts null', () => {
		const b = bookFromPageList('romans', list)!;
		expect(b.book).toEqual({ slug: 'romans', title: 'Romans', order: 45 });
		expect(b.chapters.map((c) => c.chapter)).toEqual([5, 8]);
		expect(b.verses).toEqual([{ chapter: 8, verse: 28, citing_count: 12, text: '' }]);
		expect([b.citing_count, b.books_count, b.top_books]).toEqual([null, null, []]);
	});
	it('walks prev/next in Bible order', () => {
		const b = bookFromPageList('romans', list)!;
		expect([b.prev?.book, b.next]).toEqual(['john', null]);
	});
	it('is null for a book with no chapter page, like the API', () => {
		expect(bookFromPageList('jude', list)).toBeNull();
	});
});
