import { describe, expect, it } from 'vitest';
import { buildShelves, shelfHref } from './bookshelf';
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
