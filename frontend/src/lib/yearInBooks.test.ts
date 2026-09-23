import { describe, expect, it } from 'vitest';
import { goalPace, yearStats, yearsWithData } from './yearInBooks';
import type { BookSummary } from './library-public';

const book = (slug: string, author: string, word_count: number | null = 60_000) =>
	({ slug, title: slug, word_count, author: { slug: author, name: author.toUpperCase() } }) as unknown as BookSummary;

// Midday local time, so the local year is unambiguous in any timezone.
const at = (iso: string) => new Date(`${iso}T12:00:00`).getTime();
const done = (slug: string, iso: string | null, kind: 'book' | 'sermon' = 'book') => ({
	slug,
	kind,
	order: 1,
	paragraph_index: 0,
	language: 'en',
	at: at('2026-01-01'),
	finished_at: iso ? at(iso) : null
});

const catalog = [book('a', 'murray'), book('b', 'murray'), book('c', 'spurgeon', null), book('d', 'bunyan')];

describe('yearStats', () => {
	const progress = [
		done('a', '2026-03-01'),
		done('b', '2026-08-01'),
		done('c', '2026-05-01'),
		done('d', '2025-12-31'), // last year
		done('x', '2026-06-01'), // no row in this language: counted, not drawn
		done('s', '2026-06-01', 'sermon'), // not a book
		done('e', null) // still reading
	];

	it('counts only books finished that year, newest first', () => {
		const s = yearStats({ progress, books: catalog, days: [], year: 2026, wpm: 200 });
		expect(s.finished).toBe(4);
		expect(s.books.map((b) => b.slug)).toEqual(['b', 'c', 'a']);
	});

	it('estimates hours from the finished books at the reader pace', () => {
		const s = yearStats({ progress, books: catalog, days: [], year: 2026, wpm: 200 });
		expect(s.words).toBe(120_000); // c has no word count
		expect(s.hours).toBe(10); // 120,000 / 200 / 60
	});

	it('names a most-read author only when one leads with two or more', () => {
		expect(yearStats({ progress, books: catalog, days: [], year: 2026, wpm: 200 }).topAuthor).toEqual({
			name: 'MURRAY',
			slug: 'murray',
			count: 2
		});
		expect(yearStats({ progress, books: catalog, days: [], year: 2025, wpm: 200 }).topAuthor).toBeNull();
	});

	it('counts days read and the longest streak within the year only', () => {
		const days = ['2025-12-30', '2025-12-31', '2026-01-01', '2026-01-02', '2026-02-10', '2026-02-10'];
		const s = yearStats({ progress: [], books: [], days, year: 2026, wpm: 200 });
		expect(s.daysRead).toBe(3);
		expect(s.longestStreak).toBe(2); // the run across New Year counts from Jan 1
	});
});

describe('yearsWithData', () => {
	it('lists years with a finish or a day read, newest first, always this year', () => {
		const years = yearsWithData([done('a', '2024-05-01'), done('b', null)], ['2025-02-02', 'junk'], 2026);
		expect(years).toEqual([2026, 2025, 2024]);
	});
});

describe('goalPace', () => {
	it('spreads the goal over the year and rounds the target down', () => {
		// 23 Sep 2026 is day 266 of 365: 12 × 266/365 = 8.7 → 8 expected.
		expect(goalPace(8, 12, '2026-09-23', 2026)).toEqual({ status: 'on', by: 0 });
		expect(goalPace(7, 12, '2026-09-23', 2026)).toEqual({ status: 'behind', by: 1 });
		expect(goalPace(10, 12, '2026-09-23', 2026)).toEqual({ status: 'ahead', by: 2 });
		expect(goalPace(12, 12, '2026-09-23', 2026)).toEqual({ status: 'met', by: 0 });
	});

	it('is not behind on the first day of the year', () => {
		expect(goalPace(0, 12, '2026-01-01', 2026)).toEqual({ status: 'on', by: 0 });
	});

	it('judges a past year on the whole goal', () => {
		expect(goalPace(9, 12, '2026-09-23', 2025)).toEqual({ status: 'behind', by: 3 });
	});
});
