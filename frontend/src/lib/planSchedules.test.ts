import { afterEach, describe, expect, it, vi } from 'vitest';
import { planSchedules } from './planSchedules.svelte';
import { readingSync } from './readingSync';
import { PLAN_SCHEDULE_KEY } from './reading-schema';

afterEach(() => {
	localStorage.clear();
	vi.restoreAllMocks();
});

describe('planSchedules', () => {
	it('merges a change into the plan\'s choices, stamps it, and mirrors it', () => {
		const push = vi.spyOn(readingSync, 'pushPlanSchedule').mockImplementation(() => {});
		vi.spyOn(Date, 'now').mockReturnValue(1234);
		planSchedules.set('dotk', { rule: 'weekdays' });
		planSchedules.set('dotk', { time: '06:30' });
		expect(planSchedules.get('dotk')).toEqual({ rule: 'weekdays', time: '06:30', updatedAt: 1234 });
		expect(JSON.parse(localStorage.getItem(PLAN_SCHEDULE_KEY)!).dotk.rule).toBe('weekdays');
		expect(push).toHaveBeenLastCalledWith('dotk', { rule: 'weekdays', time: '06:30', updatedAt: 1234 });
	});

	it('reads a plan with no choices as empty, and re-reads after a sync write-back', () => {
		expect(planSchedules.get('none')).toEqual({});
		localStorage.setItem(PLAN_SCHEDULE_KEY, JSON.stringify({ none: { rule: 'monsat' } }));
		window.dispatchEvent(new Event('ochorus:sync'));
		expect(planSchedules.get('none').rule).toBe('monsat');
	});
});
