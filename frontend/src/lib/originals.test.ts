import { describe, expect, it } from 'vitest';
import type { BookSummary } from './library-public';
import { ORIGINALS_SLUG, authorPath, shelveOriginals } from './originals';

const book = (slug: string, word_count: number | null = 1000) =>
	({ slug, word_count }) as BookSummary;

describe('authorPath', () => {
	it('sends the imprint to /originals and everyone else to their author page', () => {
		expect(authorPath(ORIGINALS_SLUG)).toBe('/originals');
		expect(authorPath('john-bunyan')).toBe('/authors/john-bunyan');
	});
});

describe('shelveOriginals', () => {
	const books = [
		book('brave-for-god-2', 200),
		book('tukutendereza'),
		book('brave-for-god', 300),
		book('growing-in-wisdom'),
		book('a-new-original')
	];
	const brave = [
		{ slug: 'brave-for-god', title: 'Brave for God', description: '', books: ['brave-for-god', 'brave-for-god-2'] }
	];

	it('rows each series in its volume order and totals its words', () => {
		const { series } = shelveOriginals(books, brave);
		expect(series).toHaveLength(1);
		expect(series[0].books.map((b) => b.slug)).toEqual(['brave-for-god', 'brave-for-god-2']);
		expect(series[0].words).toBe(500);
	});

	it('shelves stand-alone books by kind, with unknown ones under More', () => {
		const { shelves } = shelveOriginals(books, brave);
		expect(shelves.map((s) => [s.key, s.books.map((b) => b.slug)])).toEqual([
			['lives', ['tukutendereza']],
			['life', ['growing-in-wisdom']],
			['more', ['a-new-original']]
		]);
	});

	it('shelves a series volume alone when the series is not named in this language', () => {
		// The API leaves an unnamed series out, so its books arrive ungrouped.
		const { series, shelves } = shelveOriginals([book('rooted-1')], []);
		expect(series).toEqual([]);
		expect(shelves).toEqual([{ key: 'more', books: [book('rooted-1')] }]);
	});

	it('drops a series whose books are all missing in this language', () => {
		const { series } = shelveOriginals([], [
			{ slug: 'rooted', title: 'Rooted', description: '', books: ['rooted-1'] }
		]);
		expect(series).toEqual([]);
	});
});
