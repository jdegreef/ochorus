import { describe, expect, it } from 'vitest';
import { buildShelves, packRows, shelfHref, spineSize, customShelfItems, sortShelf } from './bookshelf';
import type { BookSummary } from './library-public';

const book = (slug: string, chapter_count = 10) =>
	({
		slug,
		title: slug,
		chapter_count,
		author: { name: 'A', slug: 'a' }
	}) as unknown as BookSummary;

const rec = (slug: string, order: number, at: number, finished_at: number | null = null) => ({
	slug,
	kind: 'book' as const,
	order,
	paragraph_index: 0,
	language: 'en',
	at,
	finished_at
});

const fav = (slug: string, at: number, kind: 'book' | 'author' = 'book') => ({
	kind,
	slug,
	at
});

describe('buildShelves', () => {
	const catalog = [book('a'), book('b'), book('c'), book('d')];

	it('puts each book on exactly one shelf, reading state outranking the heart', () => {
		const s = buildShelves(
			catalog,
			[fav('a', 1), fav('b', 2), fav('c', 3)],
			[rec('a', 4, 10), rec('b', 10, 11, 20)]
		);
		expect(s.reading.map((x) => x.book.slug)).toEqual(['a']);
		expect(s.finished.map((x) => x.book.slug)).toEqual(['b']);
		expect(s.toRead.map((x) => x.book.slug)).toEqual(['c']);
		expect(s.reading[0].saved).toBe(true);
	});

	it('shelves a started book that was never hearted', () => {
		const s = buildShelves(catalog, [], [rec('d', 2, 5)]);
		expect(s.reading).toHaveLength(1);
		expect(s.reading[0].saved).toBe(false);
	});

	it('sorts each shelf newest first by its own clock', () => {
		const s = buildShelves(
			catalog,
			[fav('c', 1), fav('d', 9)],
			[rec('a', 2, 5, 50), rec('b', 2, 40, 30)]
		);
		expect(s.toRead.map((x) => x.book.slug)).toEqual(['d', 'c']);
		// finished by finished_at, not last-read
		expect(s.finished.map((x) => x.book.slug)).toEqual(['a', 'b']);
		expect(s.finished[0].pct).toBe(100);
	});

	it('reports hearted books missing in this language, drops unhearted ones', () => {
		const s = buildShelves(catalog, [fav('zz', 1), fav('a', 1, 'author')], [rec('yy', 2, 5)]);
		expect(s.unresolved).toEqual(['zz']);
		expect(s.reading).toEqual([]);
		expect(s.toRead).toEqual([]);
	});

	it('links a book being read to its exact resume point', () => {
		const s = buildShelves(catalog, [fav('c', 1)], [{ ...rec('a', 3, 1), paragraph_index: 7 }]);
		expect(shelfHref(s.reading[0])).toBe('/books/a/3?p=7');
		expect(shelfHref(s.toRead[0])).toBe('/books/c');
	});
});

describe('spines', () => {
	it('sizes a longer book thicker, within bounds, and stably', () => {
		const thin = spineSize({ slug: 'a', word_count: 8000, chapter_count: 3 });
		const thick = spineSize({ slug: 'a', word_count: 400000, chapter_count: 40 });
		expect(thin.width).toBeLessThan(thick.width);
		expect(thick.width).toBe(44);
		expect(spineSize({ slug: 'a', word_count: null, chapter_count: 3 })).toEqual(
			spineSize({ slug: 'a', word_count: null, chapter_count: 3 })
		);
		expect(thin.height).toBeGreaterThanOrEqual(150);
		expect(thin.height).toBeLessThanOrEqual(185);
	});

	it('packs spines into rows that fit, keeping order', () => {
		expect(packRows([30, 30, 30, 30], 100, 5)).toEqual([[0, 1, 2], [3]]);
		expect(packRows([200, 10], 100, 5)).toEqual([[0], [1]]);
		expect(packRows([], 100, 5)).toEqual([]);
	});
});

describe('customShelfItems', () => {
	it('draws a chosen book with its reading status, newest-added first', () => {
		const items = customShelfItems(
			new Map([
				['a', 1],
				['c', 3],
				['zz', 9]
			]),
			[book('a'), book('b'), book('c')],
			[{ kind: 'book', slug: 'c', at: 1 }],
			[{ ...rec('a', 2, 5), finished_at: 7 }]
		);
		expect(items.map((i) => [i.book.slug, i.status, i.saved])).toEqual([
			['c', 'toRead', true],
			['a', 'finished', false]
		]);
	});
});

describe('sortShelf', () => {
	const items = customShelfItems(
		new Map([
			['b', 1],
			['a', 2],
			['c', 3]
		]),
		[
			{ ...book('b'), title: 'Été', word_count: 50_000, author: { name: 'Zed', slug: 'z' } },
			{ ...book('a'), title: 'apple', word_count: 90_000, author: { name: 'Ann', slug: 'n' } },
			{ ...book('c'), title: 'Banana', word_count: 10_000, author: { name: 'Ann', slug: 'n' } }
		] as BookSummary[],
		[],
		[]
	);
	const order = (mode: Parameters<typeof sortShelf>[1]) => sortShelf(items, mode).map((i) => i.book.slug);

	it('keeps the shelf order for recent', () => expect(order('recent')).toEqual(['c', 'a', 'b']));
	it('sorts titles case- and accent-insensitively', () => expect(order('title')).toEqual(['a', 'c', 'b']));
	it('sorts by author, then title', () => expect(order('author')).toEqual(['a', 'c', 'b']));
	it('sorts by length', () => {
		expect(order('shortest')).toEqual(['c', 'b', 'a']);
		expect(order('longest')).toEqual(['a', 'b', 'c']);
	});
});
