import { describe, expect, it } from 'vitest';
import { periodTrend, pointsTrend } from './library-admin';

describe('periodTrend', () => {
	it('reads "new" with no baseline, and nothing when both are zero', () => {
		expect(periodTrend(5, 0)).toEqual({ dir: 'up', text: 'new' });
		expect(periodTrend(0, 0)).toBeNull();
	});

	it('reports a small base as an absolute change with its baseline', () => {
		// The users page's 1 → 30 used to read "+2900%".
		expect(periodTrend(30, 1)).toEqual({ dir: 'up', text: '+29 vs 1' });
		expect(periodTrend(3, 8)).toEqual({ dir: 'down', text: '-5 vs 8' });
		expect(periodTrend(4, 4)).toEqual({ dir: 'flat', text: '0 vs 4' });
	});

	it('uses a percentage once the base is large enough to mean something', () => {
		expect(periodTrend(30, 20)).toEqual({ dir: 'up', text: '+50%' });
		expect(periodTrend(15, 20)).toEqual({ dir: 'down', text: '-25%' });
		expect(periodTrend(20, 20)).toEqual({ dir: 'flat', text: '0%' });
	});
});

describe('pointsTrend', () => {
	it('measures rates in percentage points', () => {
		expect(pointsTrend(0.16, 0.14)).toEqual({ dir: 'up', text: '+2 pts', bad: false });
		expect(pointsTrend(0.3, null)).toBeNull();
	});

	it('marks a rise as bad when lower is better', () => {
		expect(pointsTrend(0.45, 0.41, { lowerIsBetter: true })).toEqual({
			dir: 'up',
			text: '+4 pts',
			bad: true
		});
		expect(pointsTrend(0.38, 0.41, { lowerIsBetter: true })?.bad).toBe(false);
		expect(pointsTrend(0.41, 0.41, { lowerIsBetter: true })?.bad).toBe(false);
	});
});
