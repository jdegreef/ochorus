import { describe, expect, it } from 'vitest';
import { DAILY_CHAPTER_CYCLE, DAILY_CHAPTER_PATH, pickDailyChapter } from './dailyChapter';
import { localDayNumber } from './dailyArticles';

/** The local date `n` days after the first day of a turn of the path. */
const turnStart = (() => {
	const d = new Date(2026, 10, 13);
	d.setDate(d.getDate() - (localDayNumber(d) % DAILY_CHAPTER_CYCLE));
	return d;
})();
const dayOf = (n: number) => new Date(turnStart.getFullYear(), turnStart.getMonth(), turnStart.getDate() + n, 12);

describe('pickDailyChapter', () => {
	it('walks Mark, John, Genesis, Psalms and Romans, a chapter a day, then begins again', () => {
		expect(DAILY_CHAPTER_CYCLE).toBe(253);
		expect(pickDailyChapter(dayOf(0))).toEqual({
			slug: 'gospel-of-mark',
			order: 2,
			title: 'Mark 1',
			href: '/books/gospel-of-mark/2'
		});
		expect(pickDailyChapter(dayOf(15)).title).toBe('Mark 16');
		expect(pickDailyChapter(dayOf(16)).title).toBe('John 1');
		expect(pickDailyChapter(dayOf(16 + 21 + 50 + 22))).toMatchObject({ title: 'Psalm 23', order: 24 });
		expect(pickDailyChapter(dayOf(252)).title).toBe('Romans 16');
		expect(pickDailyChapter(dayOf(253)).title).toBe('Mark 1');
	});
	it('is the same all day, and the next day moves on one', () => {
		const morning = new Date(2026, 10, 13, 0, 5);
		const night = new Date(2026, 10, 13, 23, 55);
		expect(pickDailyChapter(morning)).toEqual(pickDailyChapter(night));
		expect(pickDailyChapter(new Date(2026, 10, 14, 0, 5))).not.toEqual(pickDailyChapter(night));
	});
	it('reaches every chapter of the path once per turn', () => {
		const seen = new Set(Array.from({ length: DAILY_CHAPTER_CYCLE }, (_, n) => pickDailyChapter(dayOf(n)).title));
		expect(seen.size).toBe(DAILY_CHAPTER_PATH.reduce((n, [, , c]) => n + c, 0));
	});
});
