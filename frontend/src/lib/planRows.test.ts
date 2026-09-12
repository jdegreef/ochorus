import { beforeEach, describe, it, expect, vi } from 'vitest';
import { buildPlanRows } from './planRows';
import { PLANS_KEY } from './reading-schema';
import type { PlanSummary } from './library-public';

// planProgress mirrors changes to the account; that's a no-op in these unit
// tests — we only assert the rows it resolves from the local cache.
vi.mock('./readingSync', () => ({ readingSync: { pushPlan: () => {} } }));

// Only the fields buildPlanRows reads; the rest of the summary is irrelevant.
const plan = (slug: string, title: string, day_count: number): PlanSummary =>
	({ slug, title, day_count }) as unknown as PlanSummary;

beforeEach(() => localStorage.clear());

describe('buildPlanRows', () => {
	it('is empty with no started plans', () => {
		expect(buildPlanRows([plan('advent', 'Advent', 25)])).toEqual([]);
	});

	it('flags a plan finished when every day is done, in-progress otherwise', () => {
		localStorage.setItem(
			PLANS_KEY,
			JSON.stringify({
				advent: { startedAt: 1, done: [1, 2, 3] }, // 3 of 3 → finished
				lent: { startedAt: 2, done: [1, 2] } // 2 of 5 → in progress
			})
		);
		const by = Object.fromEntries(
			buildPlanRows([plan('advent', 'Advent', 3), plan('lent', 'Lent', 5)]).map((r) => [r.slug, r])
		);
		expect(by['advent'].finished).toBe(true);
		expect(by['advent'].pct).toBe(100);
		expect(by['lent'].finished).toBe(false);
		expect(by['lent'].done).toBe(2);
		expect(by['lent'].pct).toBe(40);
	});

	it('drops a started plan with no catalog row in this language', () => {
		localStorage.setItem(PLANS_KEY, JSON.stringify({ ghost: { startedAt: 1, done: [] } }));
		expect(buildPlanRows([plan('advent', 'Advent', 25)])).toEqual([]);
	});

	it('orders newest-started first', () => {
		localStorage.setItem(
			PLANS_KEY,
			JSON.stringify({
				advent: { startedAt: 1, done: [] },
				lent: { startedAt: 5, done: [] }
			})
		);
		expect(
			buildPlanRows([plan('advent', 'Advent', 3), plan('lent', 'Lent', 3)]).map((r) => r.slug)
		).toEqual(['lent', 'advent']);
	});
});
