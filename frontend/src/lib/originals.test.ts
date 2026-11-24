import { describe, expect, it } from 'vitest';
import type { BookSummary } from './library-public';
import {
	ORIGINALS_SLUG,
	authorLdType,
	authorPath,
	hasBylinePage,
	isImprint,
	shelveOriginals,
	newestOriginals
} from './originals';
import { OWB_SLUG } from './openWordBible';

const book = (slug: string, word_count: number | null = 1000) =>
	({ slug, word_count }) as BookSummary;

describe('authorPath', () => {
	it('sends the imprint to /originals and everyone else to their author page', () => {
		expect(authorPath(ORIGINALS_SLUG)).toBe('/originals');
		expect(authorPath(OWB_SLUG)).toBe('/open-word-bible');
		// A hub locale has the page; a language without the hub goes through the
		// author route.
		expect(authorPath(OWB_SLUG, 'es')).toBe('/open-word-bible');
		expect(authorPath(OWB_SLUG, 'sw')).toBe('/authors/open-word-bible');
		expect(authorPath('john-bunyan')).toBe('/authors/john-bunyan');
	});
});

describe('bylines that are not people', () => {
	it('gives the imprint and the translation their own page, and Organization in JSON-LD', () => {
		for (const slug of [ORIGINALS_SLUG, OWB_SLUG]) {
			expect(hasBylinePage(slug)).toBe(true);
			expect(isImprint({ slug })).toBe(true);
			expect(authorLdType(slug)).toBe('Organization');
		}
		expect(hasBylinePage('john-bunyan')).toBe(false);
		expect(isImprint({ slug: 'john-bunyan' })).toBe(false);
		expect(authorLdType('john-bunyan')).toBe('Person');
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
		{
			slug: 'brave-for-god',
			title: 'Brave for God',
			description: '',
			books: ['brave-for-god', 'brave-for-god-2']
		}
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

	it('sinks a series too long for one row of covers below the short ones', () => {
		const keySlugs = Array.from({ length: 7 }, (_, i) => `key-${i + 1}`);
		const { series } = shelveOriginals(
			[...books, ...keySlugs.map((s) => book(s))],
			[
				{ slug: 'key', title: 'Key', description: '', books: keySlugs },
				brave[0],
				{ slug: 'wisdom', title: 'Wisdom', description: '', books: ['growing-in-wisdom'] }
			]
		);
		expect(series.map((s) => s.slug)).toEqual(['brave-for-god', 'wisdom', 'key']);
	});

	it('drops a series whose books are all missing in this language', () => {
		const { series } = shelveOriginals(
			[],
			[{ slug: 'rooted', title: 'Rooted', description: '', books: ['rooted-1'] }]
		);
		expect(series).toEqual([]);
	});
});

describe('newestOriginals', () => {
	const at = (slug: string, created_at: string) => ({ slug, created_at }) as BookSummary;
	it('puts the most recently added first and keeps n', () => {
		const books = [
			at('a', '2026-11-01T00:00:00Z'),
			at('b', '2026-11-19T00:00:00Z'),
			at('c', '2026-11-15T00:00:00Z')
		];
		expect(newestOriginals(books, 2).map((b) => b.slug)).toEqual(['b', 'c']);
		expect(books[0].slug).toBe('a');
	});
	it('skips a book the API sent no date for', () => {
		expect(
			newestOriginals([at('a', ''), at('b', '2026-01-01T00:00:00Z')]).map((b) => b.slug)
		).toEqual(['b']);
	});
});
