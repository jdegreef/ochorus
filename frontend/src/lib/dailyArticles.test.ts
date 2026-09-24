import { describe, expect, it } from 'vitest';
import { localDayNumber, pickDailyArticles } from './dailyArticles';

const shelf = Array.from({ length: 30 }, (_, i) => ({ slug: `article-${i}` }));
const day = (y: number, m: number, d: number, h = 12) => new Date(y, m - 1, d, h);
const slugs = (xs: { slug: string }[]) => xs.map((x) => x.slug);

describe('pickDailyArticles', () => {
	it('picks eight distinct articles', () => {
		const picks = pickDailyArticles(shelf, day(2026, 9, 23));
		expect(picks).toHaveLength(8);
		expect(new Set(slugs(picks)).size).toBe(8);
	});

	it('is the same all day and for any API order', () => {
		const morning = pickDailyArticles(shelf, day(2026, 9, 23, 0));
		const night = pickDailyArticles([...shelf].reverse(), day(2026, 9, 23, 23));
		expect(slugs(night)).toEqual(slugs(morning));
	});

	it('turns over the next day, with no overlap while the shelf is large enough', () => {
		const today = slugs(pickDailyArticles(shelf, day(2026, 9, 23)));
		const tomorrow = slugs(pickDailyArticles(shelf, day(2026, 9, 24)));
		expect(tomorrow.filter((s) => today.includes(s))).toEqual([]);
	});

	it('brings every article round within a full cycle', () => {
		const seen = new Set<string>();
		for (let d = 0; d < 4; d++) {
			for (const a of pickDailyArticles(shelf, day(2026, 9, 23 + d))) seen.add(a.slug);
		}
		expect(seen.size).toBe(shelf.length);
	});

	it('returns a short shelf whole', () => {
		expect(pickDailyArticles(shelf.slice(0, 5), day(2026, 9, 23))).toHaveLength(5);
	});
});

describe('localDayNumber', () => {
	it('counts calendar days, ignoring the time of day', () => {
		expect(localDayNumber(day(2026, 9, 24, 0))).toBe(localDayNumber(day(2026, 9, 23, 23)) + 1);
	});
});
