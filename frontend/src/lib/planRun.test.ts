import { describe, expect, it } from 'vitest';
import { dayChapters, planDayCovering, runStep } from './planRun';

const day = (day: number, book_slug: string, chapter_order: number | null, chapter_count?: number, article_slug = '') => ({
	day,
	book_slug,
	chapter_order,
	chapter_count,
	article_slug
});

describe('dayChapters', () => {
	it('reads the run from chapter_order', () => {
		expect(dayChapters(day(1, 'genesis', 2, 3))).toEqual([2, 3, 4]);
	});
	it('is one chapter when the API predates chapter_count', () => {
		expect(dayChapters(day(1, 'genesis', 5))).toEqual([5]);
	});
	it('is empty on an article day', () => {
		expect(dayChapters(day(1, '', null, 1, 'what-is-grace'))).toEqual([]);
	});
});

describe('planDayCovering', () => {
	const days = [day(1, 'genesis', 2, 3), day(2, 'genesis', 5, 2), day(3, '', null, 1, 'a'), day(4, 'genesis', 7, 1)];
	it('finds the day whose run holds the chapter', () => {
		expect(planDayCovering(days, 'genesis', 3, 1)?.day).toBe(1);
		expect(planDayCovering(days, 'genesis', 6, 1)?.day).toBe(2);
	});
	it('only the current day or a neighbour', () => {
		expect(planDayCovering(days, 'genesis', 7, 2)).toBeNull();
		expect(planDayCovering(days, 'genesis', 7, 0)?.day).toBe(4);
	});
	it('another book is not the plan', () => {
		expect(planDayCovering(days, 'exodus', 3, 1)).toBeNull();
	});
});

describe('runStep', () => {
	it('names the place in the run and the chapter after', () => {
		expect(runStep(day(1, 'genesis', 2, 3), 2)).toEqual({ n: 1, m: 3, next: 3 });
		expect(runStep(day(1, 'genesis', 2, 3), 4)).toEqual({ n: 3, m: 3, next: null });
	});
	it('is null on a one-chapter day or a chapter outside the run', () => {
		expect(runStep(day(1, 'genesis', 2, 1), 2)).toBeNull();
		expect(runStep(day(1, 'genesis', 2, 3), 9)).toBeNull();
	});
});
