import { afterEach, describe, expect, it, vi } from 'vitest';
import { planTogether } from './planTogether.svelte';
import { readingSync } from './readingSync';
import { PLAN_SCHEDULE_KEY, PLAN_TOGETHER_KEY, SIGN_OUT_DATA_KEYS } from './reading-schema';

afterEach(() => {
	localStorage.clear();
	vi.restoreAllMocks();
});

describe('planTogether', () => {
	it('keeps a joined group on this device only — nothing pushed, no schedule written', () => {
		const pushSchedule = vi.spyOn(readingSync, 'pushPlanSchedule').mockImplementation(() => {});
		const pushPlan = vi.spyOn(readingSync, 'pushPlan').mockImplementation(() => {});
		planTogether.join('humility-12-days', { start: '2026-10-12', rule: 'weekdays' });
		expect(planTogether.get('humility-12-days')).toEqual({ start: '2026-10-12', rule: 'weekdays' });
		expect(JSON.parse(localStorage.getItem(PLAN_TOGETHER_KEY)!)).toHaveProperty('humility-12-days');
		expect(localStorage.getItem(PLAN_SCHEDULE_KEY)).toBeNull();
		expect(pushSchedule).not.toHaveBeenCalled();
		expect(pushPlan).not.toHaveBeenCalled();
	});

	it('forgets a group on leave', () => {
		planTogether.join('p', { start: '2026-10-12', rule: 'daily' });
		planTogether.leave('p');
		expect(planTogether.get('p')).toBeNull();
	});

	it('reads a row that no longer parses as no group', () => {
		localStorage.setItem(PLAN_TOGETHER_KEY, JSON.stringify({ p: { start: 'soon', rule: 'daily' } }));
		window.dispatchEvent(new Event('ochorus:sync'));
		expect(planTogether.get('p')).toBeNull();
	});

	it("keeps a group's totals code, and drops one that isn't a code", () => {
		planTogether.join('p', { start: '2026-10-12', rule: 'daily', group: 'KunYdx4NiTLQ' });
		expect(planTogether.get('p')?.group).toBe('KunYdx4NiTLQ');
		localStorage.setItem(PLAN_TOGETHER_KEY, JSON.stringify({ p: { start: '2026-10-12', rule: 'daily', group: '<x>' } }));
		window.dispatchEvent(new Event('ochorus:sync'));
		expect(planTogether.get('p')).toEqual({ start: '2026-10-12', rule: 'daily' });
	});

	it('goes with the reading data on sign-out', () => {
		expect(SIGN_OUT_DATA_KEYS).toContain(PLAN_TOGETHER_KEY);
	});
});
