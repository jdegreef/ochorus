import { describe, expect, it } from 'vitest';
import {
	groupBySeries,
	nextInSeries,
	seriesAmong,
	seriesFromBooks,
	seriesCardProgressLabel,
	seriesProgress,
	seriesCompanion,
	cardLanguages,
	seriesToContinue,
	splitSeriesTitle,
	type BookStage,
	seriesLabel,
	groupByAudience,
	seriesAges
} from './series';
import { tileFace, type BookSeries, type BookSummary } from './library-public';

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
		expect(seriesProgress(['a', 'b', 'c'], of)).toEqual({
			done: 1,
			total: 3,
			started: true,
			stages: ['done', 'reading', 'unread']
		});
	});

	it('is not started when no book is opened', () => {
		expect(seriesProgress(['c', 'd'], of)).toEqual({
			done: 0,
			total: 2,
			started: false,
			stages: ['unread', 'unread']
		});
	});
});

describe('seriesCardProgressLabel', () => {
	it('says a series is in progress before any book is finished', () => {
		expect(seriesCardProgressLabel(['reading', 'unread', 'unread', 'unread'], 'en')).toBe(
			'In progress'
		);
	});

	it('counts finished books once there are any', () => {
		const stages: BookStage[] = ['done', 'done', 'reading', 'unread'];
		expect(seriesCardProgressLabel(stages, 'en')).toBe('2 of 4 read');
	});
});

describe('seriesToContinue', () => {
	const state: Record<string, { started: boolean; finished: boolean }> = {
		'r-1': { started: true, finished: true },
		'r-2': { started: true, finished: false },
		'b-1': { started: true, finished: false },
		'd-1': { started: true, finished: true }
	};
	const of = (slug: string) => state[slug] ?? { started: false, finished: false };
	const at: Record<string, number> = { 'r-1': 1, 'r-2': 5, 'b-1': 9, 'd-1': 3 };
	const lastRead = (slug: string) => at[slug] ?? 0;
	const rooted = { slug: 'rooted', books: ['r-1', 'r-2', 'r-3'] };
	const brave = { slug: 'brave', books: ['b-1', 'b-2'] };
	const done = { slug: 'done', books: ['d-1'] };
	const fresh = { slug: 'fresh', books: ['f-1'] };

	it('lists begun, unfinished series, most recently read first', () => {
		const rows = seriesToContinue([rooted, brave, done, fresh], of, lastRead);
		expect(rows.map((r) => [r.series.slug, r.slug])).toEqual([
			['brave', 'b-1'],
			['rooted', 'r-2']
		]);
		expect(rows[1].stages).toEqual(['done', 'reading', 'unread']);
	});

	it('caps the list', () => {
		expect(seriesToContinue([rooted, brave], of, lastRead, 1)).toHaveLength(1);
	});

	it('skips a series with no book list', () => {
		const old: { slug: string; books?: string[] } = { slug: 'old' };
		expect(seriesToContinue([old], of, lastRead)).toEqual([]);
	});
});

describe('splitSeriesTitle', () => {
	it('splits at a spaced en dash', () => {
		expect(splitSeriesTitle('Daughters of the King – 30 Days with God for Girls')).toEqual({
			name: 'Daughters of the King',
			subtitle: '30 Days with God for Girls'
		});
	});

	it('splits at a spaced em dash (the Hindi titles)', () => {
		const { name } = splitSeriesTitle('जड़ें जमाए — युवाओं के लिये परमेश्वर के साथ 30 दिन');
		expect(name).toBe('जड़ें जमाए');
	});

	it('leaves a title with no spaced dash whole', () => {
		expect(splitSeriesTitle('Brave for God')).toEqual({ name: 'Brave for God', subtitle: '' });
		expect(splitSeriesTitle('Ages 9–12').subtitle).toBe('');
	});

	it('never returns an empty name or subtitle', () => {
		expect(splitSeriesTitle('Rooted – ')).toEqual({ name: 'Rooted – ', subtitle: '' });
		expect(splitSeriesTitle(' – Rooted').name).toBe(' – Rooted');
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
	const face = (slug: string) => ({
		slug,
		language: 'en',
		title: slug,
		subtitle: '',
		cover_title: '',
		cover_url: `/covers/${slug}.svg`,
		cover_color: '#000',
		author: { slug: 'ochorus', name: 'Ochorus', birth_year: null }
	});
	const vol = (slug: string, series: string, position: number) => ({
		...face(slug),
		series_position: position,
		series: { slug: series, title: series.toUpperCase(), position, total: 6 }
	});

	it("builds a card per series from the shelf's volumes, in reading order", () => {
		const cards = seriesFromBooks([
			vol('r-2', 'rooted', 2),
			{ ...face('plain'), series: null },
			vol('r-1', 'rooted', 1)
		]);
		expect(cards).toHaveLength(1);
		expect(cards[0]).toMatchObject({ slug: 'rooted', title: 'ROOTED', book_count: 2, books: ['r-1', 'r-2'] });
		expect(cards[0].covers.map((c) => c.slug)).toEqual(['r-1', 'r-2']);
		// Each tile carries its face, so the fan draws the title over a plate.
		const tile = cards[0].covers[0];
		expect(tile.kind === 'book' && tileFace(tile)?.author.name).toBe('Ochorus');
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

describe('cardLanguages', () => {
	it("puts the reader's language first and the rest in code order", () => {
		expect(cardLanguages(['fr', 'en', 'es'], 'es')).toEqual({ shown: ['es', 'en', 'fr'], hidden: [] });
	});

	it('caps the list and counts the rest', () => {
		const all = ['am', 'ar', 'en', 'es', 'fr', 'hi', 'lg', 'pt', 'sw', 'uk'];
		expect(cardLanguages(all, 'en')).toEqual({
			shown: ['en', 'am', 'ar', 'es', 'fr'],
			hidden: ['hi', 'lg', 'pt', 'sw', 'uk']
		});
	});

	it('shows nothing for a one-language series', () => {
		expect(cardLanguages(['en'], 'en')).toEqual({ shown: [], hidden: [] });
		expect(cardLanguages([], 'en')).toEqual({ shown: [], hidden: [] });
	});

	it('keeps a series not held in the reader language in code order', () => {
		expect(cardLanguages(['sw', 'en'], 'fr').shown).toEqual(['en', 'sw']);
	});
});

describe('seriesCompanion', () => {
	const list = [{ slug: 'daughters-of-the-king' }, { slug: 'sons-of-the-king' }, { slug: 'rooted' }];

	it('finds the other series of a pair, both ways', () => {
		expect(seriesCompanion('daughters-of-the-king', list)?.slug).toBe('sons-of-the-king');
		expect(seriesCompanion('sons-of-the-king', list)?.slug).toBe('daughters-of-the-king');
	});

	it('is null for a series with no pair, or whose pair has no page here', () => {
		expect(seriesCompanion('rooted', list)).toBeNull();
		expect(seriesCompanion('sons-of-the-king', [{ slug: 'sons-of-the-king' }])).toBeNull();
	});
});
