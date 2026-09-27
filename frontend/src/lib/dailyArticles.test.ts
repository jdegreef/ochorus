import { describe, expect, it } from 'vitest';
import { localDayNumber, pickDailyArticles } from './dailyArticles';

const shelf = Array.from({ length: 130 }, (_, i) => ({ slug: `article-${i}` }));
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

	it('turns over the next day', () => {
		const today = slugs(pickDailyArticles(shelf, day(2026, 9, 23)));
		const tomorrow = slugs(pickDailyArticles(shelf, day(2026, 9, 24)));
		expect(tomorrow.filter((s) => today.includes(s)).length).toBeLessThan(4);
	});

	it('changes at most one pick when an article is published or unpublished', () => {
		const date = day(2026, 9, 23);
		const today = slugs(pickDailyArticles(shelf, date));
		const added = slugs(pickDailyArticles([...shelf, { slug: 'brand-new' }], date));
		expect(added.filter((s) => !today.includes(s)).length).toBeLessThanOrEqual(1);
		const removed = slugs(pickDailyArticles(shelf.filter((a) => a.slug !== today[0]), date));
		expect(removed.filter((s) => !today.includes(s)).length).toBeLessThanOrEqual(1);
	});

	it('brings most of the shelf round within a month', () => {
		const seen = new Set<string>();
		for (let d = 0; d < 30; d++) {
			for (const a of pickDailyArticles(shelf, day(2026, 9, 1 + d))) seen.add(a.slug);
		}
		expect(seen.size).toBeGreaterThan(shelf.length * 0.75);
	});

	it('shows nothing when the shelf is shorter than the heading promises', () => {
		expect(pickDailyArticles(shelf.slice(0, 7), day(2026, 9, 23))).toEqual([]);
		expect(pickDailyArticles(shelf.slice(0, 8), day(2026, 9, 23))).toHaveLength(8);
	});
});

describe('pickDailyArticles with a cap', () => {
	const mixed = Array.from({ length: 130 }, (_, i) => ({ slug: i % 2 ? `book-${i}-guide` : `article-${i}` }));
	const cap = { match: (a: { slug: string }) => a.slug.endsWith('-guide'), max: 2 };
	const guides = (xs: { slug: string }[]) => xs.filter(cap.match).length;

	it('shows at most two guides, every day of a month', () => {
		for (let d = 0; d < 30; d++) {
			const picks = pickDailyArticles(mixed, day(2026, 9, 1 + d), 8, cap);
			expect(picks).toHaveLength(8);
			expect(new Set(slugs(picks)).size).toBe(8);
			expect(guides(picks)).toBeLessThanOrEqual(2);
		}
	});

	it('tops up with guides when there are too few other articles', () => {
		const shelf = [...mixed.filter(cap.match).slice(0, 10), { slug: 'a' }, { slug: 'b' }];
		const picks = pickDailyArticles(shelf, day(2026, 9, 23), 8, cap);
		expect(picks).toHaveLength(8);
		expect(slugs(picks)).toEqual(expect.arrayContaining(['a', 'b']));
	});
});

describe('localDayNumber', () => {
	it('counts calendar days, ignoring the time of day', () => {
		expect(localDayNumber(day(2026, 9, 24, 0))).toBe(localDayNumber(day(2026, 9, 23, 23)) + 1);
	});
});
