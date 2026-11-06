import { beforeEach, describe, expect, it } from 'vitest';
import { PLANS_KEY } from './reading-schema';
import { pickPlan } from './todaysPlan';
import type { PlanSummary } from './library-public';

const plan = (slug: string, day_count = 3) => ({ slug, day_count }) as PlanSummary;
const store = (s: Record<string, { startedAt: number; done: number[] }>) =>
	localStorage.setItem(PLANS_KEY, JSON.stringify(s));

const plans = [plan('a'), plan('b'), plan('c')];

describe('pickPlan', () => {
	beforeEach(() => localStorage.clear());

	it('takes the most recently started plan that has a day left', () => {
		store({
			b: { startedAt: 1, done: [1] },
			c: { startedAt: 3, done: [1, 2, 3] }, // newest, but finished
			gone: { startedAt: 4, done: [] } // not in this language's list
		});
		expect(pickPlan(plans)?.slug).toBe('b');
		expect(pickPlan(plans, true)?.slug).toBe('b');
	});

	it('offers an invitation only when asked for one', () => {
		store({ a: { startedAt: 1, done: [1, 2, 3] } });
		// Not the finished catalog-first plan: the first with a day left.
		expect(pickPlan(plans)?.slug).toBe('b');
		// The home's "Continue reading" wants a plan under way, or none.
		expect(pickPlan(plans, true)).toBeNull();
	});

	it('falls back to the first plan when every one is finished', () => {
		store({ a: { startedAt: 1, done: [1, 2, 3] } });
		expect(pickPlan([plan('a')])?.slug).toBe('a');
		expect(pickPlan([])).toBeNull();
	});
});
