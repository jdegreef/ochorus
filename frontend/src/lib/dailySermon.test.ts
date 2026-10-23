import { describe, expect, it } from 'vitest';
import { pickDailySermon } from './dailySermon';

// A lopsided shelf, like the real one: one preacher with far more sermons.
const shelf = [
	...Array.from({ length: 40 }, (_, i) => ({ slug: `spurgeon-${i}`, author: { slug: 'spurgeon' } })),
	...['wesley', 'edwards', 'moody', 'finney', 'tozer'].flatMap((a) =>
		Array.from({ length: 3 }, (_, i) => ({ slug: `${a}-${i}`, author: { slug: a } }))
	)
];
const day = (y: number, m: number, d: number, h = 12) => new Date(y, m - 1, d, h);
const days = (n: number) => Array.from({ length: n }, (_, i) => day(2026, 10, 1 + i));

describe('pickDailySermon', () => {
	it('is null on an empty shelf', () => {
		expect(pickDailySermon([], day(2026, 10, 23))).toBeNull();
	});

	it('is the same all day and for any API order', () => {
		const morning = pickDailySermon(shelf, day(2026, 10, 23, 0));
		const night = pickDailySermon([...shelf].reverse(), day(2026, 10, 23, 23));
		expect(night?.slug).toBe(morning?.slug);
	});

	it('is a different preacher every day', () => {
		const preachers = days(30).map((d) => pickDailySermon(shelf, d)!.author.slug);
		for (let i = 1; i < preachers.length; i++) expect(preachers[i]).not.toBe(preachers[i - 1]);
	});

	it('gives every preacher an equal turn, however deep their shelf', () => {
		const preachers = days(6).map((d) => pickDailySermon(shelf, d)!.author.slug);
		expect(new Set(preachers).size).toBe(6);
	});

	it("walks through a preacher's sermons on successive turns", () => {
		const picks = days(6 * 3).map((d) => pickDailySermon(shelf, d)!);
		const wesley = picks.filter((s) => s.author.slug === 'wesley').map((s) => s.slug);
		expect(new Set(wesley).size).toBe(3);
	});
});
