import { describe, it, expect } from 'vitest';
import { buildHeatmap, weekReadCount } from './heatmap';
import { shiftDay as shift } from './streak';

describe('buildHeatmap', () => {
	it('lays out weeks columns of 7 Sunday→Saturday cells', () => {
		const g = buildHeatmap([], '2026-07-25', 4);
		expect(g.weeks).toHaveLength(4);
		for (const col of g.weeks) expect(col).toHaveLength(7);
		// Row 0 is always a Sunday, row 6 a Saturday.
		expect(new Date(g.weeks[0][0].iso + 'T00:00:00Z').getUTCDay()).toBe(0);
		expect(new Date(g.weeks[0][6].iso + 'T00:00:00Z').getUTCDay()).toBe(6);
	});

	it('marks read days and never marks future days as read', () => {
		// 2026-07-25 is a Saturday; its week is the last column.
		const g = buildHeatmap(['2026-07-22', '2099-01-01'], '2026-07-22', 2);
		const flat = g.weeks.flat();
		expect(flat.find((c) => c.iso === '2026-07-22')?.read).toBe(true);
		// Days after today are flagged future and are not read.
		const future = flat.filter((c) => c.future);
		expect(future.every((c) => !c.read)).toBe(true);
		expect(future.some((c) => c.iso > '2026-07-22')).toBe(true);
	});

	it('labels each month once, at the column it starts', () => {
		const g = buildHeatmap([], '2026-07-25', 12);
		const labels = g.monthLabels.map((m) => m.label);
		expect(new Set(labels).size).toBe(labels.length); // no repeats
		expect(g.monthLabels[0].col).toBeGreaterThanOrEqual(0);
	});
});

describe('weekReadCount', () => {
	it('counts distinct read days from Sunday through today', () => {
		// Week of Sun 2026-07-19 … today Wed 2026-07-22.
		const days = ['2026-07-19', '2026-07-20', '2026-07-22', '2026-07-25'];
		expect(weekReadCount(days, '2026-07-22')).toBe(3); // 19,20,22 — not the 25th (future)
	});

	it('is 0 when nothing was read this week', () => {
		expect(weekReadCount(['2026-07-01'], '2026-07-22')).toBe(0);
	});
});

describe('run shading', () => {
	it('shades the grid by tier, and leaves unread and future days at level 0', () => {
		const days = Array.from({ length: 40 }, (_, i) => shift('2026-06-01', i));
		const flat = buildHeatmap([...days, '2026-07-24'], '2026-07-20', 10).weeks.flat();
		const level = (iso: string) => flat.find((c) => c.iso === iso)?.level;
		expect(level('2026-06-01')).toBe(1); // day 1 of the run
		expect(level('2026-06-07')).toBe(2); // day 7: flame
		expect(level('2026-06-30')).toBe(3); // day 30: blaze
		expect(level('2026-07-11')).toBe(0); // the run ended on 07-10
		// Never shade a future day, even if the log somehow holds one.
		expect(flat.find((c) => c.iso === '2026-07-24')).toMatchObject({ future: true, read: false, level: 0 });
	});

	it('measures runs over runsFrom, so a slice keeps a run begun before it', () => {
		const dec = Array.from({ length: 10 }, (_, i) => shift('2025-12-22', i)); // to 2025-12-31
		const jan = Array.from({ length: 5 }, (_, i) => shift('2026-01-01', i));
		const flat = buildHeatmap(jan, '2026-01-05', 2, 'en', [...dec, ...jan]).weeks.flat();
		expect(flat.find((c) => c.iso === '2026-01-01')?.level).toBe(2); // day 11
		expect(flat.find((c) => c.iso === '2025-12-31')?.read).toBe(false); // outside the slice
	});

	it('survives a malformed log entry', () => {
		expect(() => buildHeatmap(['', '2026-7-1', '2026-07-01'], '2026-07-02', 2)).not.toThrow();
	});
});
