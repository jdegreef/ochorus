import { describe, expect, it } from 'vitest';
import { nextInSeries, seriesLabel } from './series';
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
