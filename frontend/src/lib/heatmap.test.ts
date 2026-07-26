import { describe, it, expect } from 'vitest';
import { buildHeatmap, weekReadCount } from './heatmap';

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
