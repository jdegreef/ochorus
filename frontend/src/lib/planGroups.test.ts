import { describe, expect, it } from 'vitest';
import type { PlanDay } from './library-public';
import { groupPlanDays, weeksOf } from './planGroups';

const day = (n: number, book: string, article = ''): PlanDay => ({
	day: n,
	book_slug: article ? '' : book,
	chapter_order: article ? null : n,
	article_slug: article || undefined,
	book_title: article ? '' : book.toUpperCase(),
	chapter_title: `T${n}`,
	word_count: 400
});

describe('groupPlanDays', () => {
	it('groups consecutive days by book, with their day spans', () => {
		const g = groupPlanDays([day(1, 'a'), day(2, 'a'), day(3, 'b'), day(4, 'b'), day(5, 'c')]);
		expect(g.map((x) => [x.bookSlug, x.bookTitle, x.first, x.last])).toEqual([
			['a', 'A', 1, 2],
			['b', 'B', 3, 4],
			['c', 'C', 5, 5]
		]);
	});

	it('keeps an article day in the run it sits in', () => {
		const g = groupPlanDays([day(1, 'a'), day(2, '', 'art'), day(3, 'a'), day(4, 'b')]);
		expect(g.map((x) => x.days.map((d) => d.day))).toEqual([[1, 2, 3], [4]]);
	});

	it('lets articles before any book open a run that takes the first book', () => {
		const g = groupPlanDays([day(1, '', 'welcome'), day(2, 'a'), day(3, 'b')]);
		expect(g.map((x) => [x.bookSlug, x.first, x.last])).toEqual([
			['a', 1, 2],
			['b', 3, 3]
		]);
	});

	it('opens a second run when a book comes back, with distinct keys', () => {
		const g = groupPlanDays([day(1, 'a'), day(2, 'b'), day(3, 'a')]);
		expect(g.map((x) => x.bookSlug)).toEqual(['a', 'b', 'a']);
		expect(new Set(g.map((x) => x.key)).size).toBe(3);
	});
});

describe('weeksOf', () => {
	it('cuts days into sevens, the last week short', () => {
		const days = Array.from({ length: 32 }, (_, i) => day(i + 1, 'a'));
		expect(weeksOf(days).map((w) => w.length)).toEqual([7, 7, 7, 7, 4]);
		expect(weeksOf(days.slice(0, 5)).length).toBe(1);
	});
});
