import { describe, expect, it } from 'vitest';
import {
	groupBySeries,
	nextInSeries,
	seriesAmong,
	seriesFromBooks,
	seriesProgress,
	seriesLabel,
	groupByAudience,
	seriesAges
} from './series';
import type { BookSeries, BookSummary } from './library-public';

const rooted: BookSeries = {
	slug: 'rooted',
	title: 'Rooted',
	position: 2,
	total: 6,
	previous: null,
	next: null
};

describe('seriesLabel', () => {
	it('numbers an ordered series', () => {
		expect(seriesLabel(rooted, 'en')).toBe('Book 2 of 6 in Rooted');
	});

	it('names a collection without a number', () => {
		const collection = { ...rooted, title: 'The Key Teachings', position: null, total: 4 };
		expect(seriesLabel(collection, 'en')).toBe('Part of The Key Teachings');
	});

	it("sets the numbers in the edition's own digits, as the cover ring does", () => {
		expect(seriesLabel(rooted, 'fa')).toBe('Book ۲ of ۶ in Rooted');
	});
});

describe('nextInSeries', () => {
	const books = ['one', 'two', 'three'].map((slug) => ({ slug }) as BookSummary);
	const progress =
		(started: string[], finished: string[] = []) =>
		(slug: string) => ({ started: started.includes(slug), finished: finished.includes(slug) });

	it('starts a new reader on the first book', () => {
		expect(nextInSeries(books, progress([]))).toEqual({ book: books[0], resume: false });
	});

	it('returns a reader to the book they are partway through, even out of order', () => {
		expect(nextInSeries(books, progress(['three']))).toEqual({ book: books[2], resume: true });
	});

	it('moves on to the first unfinished book once the last one read is done', () => {
		expect(nextInSeries(books, progress(['one'], ['one']))).toEqual({
			book: books[1],
			resume: false
		});
	});

	it('has nothing left once every book is finished', () => {
		const all = books.map((b) => b.slug);
		expect(nextInSeries(books, progress(all, all))).toBeNull();
	});
});

describe('groupBySeries', () => {
	const line = (slug: string, position: number | null) => ({
		slug,
		title: slug.toUpperCase(),
		position,
		total: 3
	});
	const book = (id: string, series: ReturnType<typeof line> | null) => ({ id, series });

	it('groups in the index order, volumes in reading order, loose books last in given order', () => {
		const books = [
			book('plain-b', null),
			book('rooted-3', line('rooted', 3)),
			book('kt-nee', line('key-teachings', null)),
			book('rooted-1', line('rooted', 1)),
			book('plain-a', null),
			book('kt-baxter', line('key-teachings', null))
		];
		const { named, standalone } = groupBySeries(books, ['key-teachings', 'rooted']);
		expect(named.map((g) => [g.slug, g.title, g.books.map((b) => b.id)])).toEqual([
			// A collection keeps the order it was given.
			['key-teachings', 'KEY-TEACHINGS', ['kt-nee', 'kt-baxter']],
			['rooted', 'ROOTED', ['rooted-1', 'rooted-3']]
		]);
		expect(standalone.map((b) => b.id)).toEqual(['plain-b', 'plain-a']);
	});

	it('puts a series the index does not list after the ones it does', () => {
		const { named } = groupBySeries(
			[book('x-1', line('unlisted', 1)), book('r-1', line('rooted', 1))],
			['rooted']
		);
		expect(named.map((g) => g.slug)).toEqual(['rooted', 'unlisted']);
	});
});

describe('seriesProgress', () => {
	const state: Record<string, { started: boolean; finished: boolean }> = {
		a: { started: true, finished: true },
		b: { started: true, finished: false }
	};
	const of = (slug: string) => state[slug] ?? { started: false, finished: false };

	it('counts finished books and notices any begun one', () => {
		expect(seriesProgress(['a', 'b', 'c'], of)).toEqual({ done: 1, total: 3, started: true });
	});

	it('is not started when no book is opened', () => {
		expect(seriesProgress(['c', 'd'], of)).toEqual({ done: 0, total: 2, started: false });
	});
});

describe('seriesAmong', () => {
	it('keeps the series with a book present, in the series order', () => {
		const series = [{ slug: 'kt' }, { slug: 'bfg' }, { slug: 'rooted' }];
		const books = [
			{ series: { slug: 'rooted', title: 'R', position: 1, total: 6 } },
			{ series: null },
			{ series: { slug: 'kt', title: 'K', position: null, total: 4 } }
		];
		expect(seriesAmong(series, books).map((s) => s.slug)).toEqual(['kt', 'rooted']);
	});
});

describe('seriesFromBooks', () => {
	const vol = (slug: string, series: string, position: number) => ({
		slug,
		title: slug,
		cover_url: `/covers/${slug}.png`,
		cover_color: '#000',
		series: { slug: series, title: series.toUpperCase(), position, total: 6 }
	});

	it("builds a card per series from the shelf's volumes, in reading order", () => {
		const cards = seriesFromBooks([
			vol('r-2', 'rooted', 2),
			{ slug: 'plain', title: 'Plain', cover_url: '', cover_color: '', series: null },
			vol('r-1', 'rooted', 1)
		]);
		expect(cards).toHaveLength(1);
		expect(cards[0]).toMatchObject({ slug: 'rooted', title: 'ROOTED', book_count: 2, books: ['r-1', 'r-2'] });
		expect(cards[0].covers.map((c) => c.slug)).toEqual(['r-1', 'r-2']);
	});
});

describe('groupByAudience', () => {
	it('groups in reading-age order, untagged last, keeping the list order', () => {
		const list = [
			{ slug: 'kt', audience: 'adults' as const },
			{ slug: 'bfg', audience: 'young_readers' as const },
			{ slug: 'new', audience: '' as const },
			{ slug: 'rooted', audience: 'young_readers' as const },
			{ slug: 'old-api' }
		];
		expect(groupByAudience(list).map((g) => [g.audience, g.series.map((s) => s.slug)])).toEqual([
			['young_readers', ['bfg', 'rooted']],
			['adults', ['kt']],
			[null, ['new', 'old-api']]
		]);
	});
});

describe('seriesAges', () => {
	it('prints a range, an open range, or nothing', () => {
		expect(seriesAges({ min_age: 9, max_age: 12 })).toBe('Ages 9–12');
		expect(seriesAges({ min_age: 13, max_age: null })).toBe('Ages 13+');
		expect(seriesAges({ min_age: null, max_age: null })).toBe('');
		expect(seriesAges({})).toBe('');
	});
});
