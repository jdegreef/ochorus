import { describe, expect, it } from 'vitest';

import { columnShares, headline } from './engagementCohorts';

const row = (week: string, size: number, active: number[] | null) => ({ week, size, active });

describe('columnShares', () => {
	it('weights each column by cohort size and skips hidden or unreached cohorts', () => {
		const rows = [row('a', 10, [5, 2]), row('b', 4, null), row('c', 5, [5])];
		const [w0, w1, w2] = columnShares(rows, 3);
		expect(w0).toEqual({ readers: 10, people: 15, pct: 67 });
		expect(w1).toEqual({ readers: 2, people: 10, pct: 20 });
		expect(w2).toBeNull();
	});
});

describe('headline', () => {
	it('compares week 4 for the newer half of the cohorts that reached it with the older half', () => {
		const rows = [
			row('w1', 10, [5, 4, 3, 2, 1]),
			row('w2', 10, [5, 4, 3, 2, 1, 1]),
			row('w3', 10, [9, 8, 7, 6, 4]),
			row('w4', 6, null),
			row('w5', 10, [5, 3, 2])
		];
		expect(headline(rows)).toEqual({
			earlier: { readers: 1, people: 10, pct: 10, from: 'w1', to: 'w1' },
			recent: { readers: 5, people: 20, pct: 25, from: 'w2', to: 'w3' }
		});
	});

	it('waits for two cohorts to reach week 4', () => {
		expect(headline([row('w1', 10, [5, 4, 3, 2, 1]), row('w2', 10, [5])])).toBeNull();
	});
});
