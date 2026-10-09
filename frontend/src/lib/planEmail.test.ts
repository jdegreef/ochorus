import { beforeEach, describe, expect, it, vi } from 'vitest';
import { REMINDER_TIME_KEY } from './reminder';

const schedules = vi.hoisted(() => {
	const store: Record<string, Record<string, unknown>> = {};
	return {
		store,
		get: (slug: string) => store[slug] ?? {},
		set: vi.fn((slug: string, patch: Record<string, unknown>) => {
			store[slug] = { ...store[slug], ...patch };
		})
	};
});
vi.mock('./planSchedules.svelte', () => ({ planSchedules: schedules }));
const sheet = vi.hoisted(() => ({ show: vi.fn() }));
vi.mock('./signInSheet.svelte', () => ({ signInSheet: sheet }));

const {
	HOLD_MS,
	applyHeldPlanEmail,
	askForPlanEmail,
	declinePlanEmail,
	planEmailDeclined,
	turnOffPlanEmail,
	turnOnPlanEmail
} = await import('./planEmail');

beforeEach(() => {
	localStorage.clear();
	schedules.set.mockClear();
	sheet.show.mockClear();
	for (const k of Object.keys(schedules.store)) delete schedules.store[k];
});

describe('planEmail', () => {
	it('turns the email on with the chosen time, writing only those two fields', () => {
		schedules.store.humility = { rule: 'weekdays' };
		turnOnPlanEmail('humility', '06:30');
		expect(schedules.set).toHaveBeenCalledWith('humility', { time: '06:30', email: true });
		expect(schedules.store.humility).toEqual({ rule: 'weekdays', time: '06:30', email: true });
	});

	it("without a time, uses the plan's own, else the reader's Settings reminder time", () => {
		turnOnPlanEmail('humility');
		expect(schedules.store.humility).toMatchObject({ time: '07:00', email: true });
		localStorage.setItem(REMINDER_TIME_KEY, '21:00');
		turnOnPlanEmail('other-plan');
		expect(schedules.store['other-plan']).toMatchObject({ time: '21:00' });
		schedules.store.third = { time: '05:45' };
		turnOnPlanEmail('third');
		expect(schedules.store.third).toMatchObject({ time: '05:45' });
	});

	it('turns it off for that plan alone, touching nothing else', () => {
		turnOffPlanEmail('humility');
		expect(schedules.set).toHaveBeenCalledWith('humility', { email: false });
	});

	it('signed out: holds the choice and opens the sign-up panel for its source', () => {
		askForPlanEmail('humility', 'plan_day', '06:30');
		expect(sheet.show).toHaveBeenCalledWith('plan_day');
		expect(schedules.set).not.toHaveBeenCalled();
	});

	it('turns a held choice on once, however the account arrives', () => {
		askForPlanEmail('humility', 'plan_day', '06:30');
		expect(applyHeldPlanEmail()).toBe('humility');
		expect(schedules.store.humility).toMatchObject({ time: '06:30', email: true });
		schedules.set.mockClear();
		expect(applyHeldPlanEmail()).toBeNull();
		expect(schedules.set).not.toHaveBeenCalled();
	});

	it('lets a choice older than 15 minutes lapse, and drops it', () => {
		const asked = Date.now();
		askForPlanEmail('humility', 'plan_start', '06:30');
		expect(applyHeldPlanEmail(asked + HOLD_MS + 1)).toBeNull();
		expect(schedules.set).not.toHaveBeenCalled();
		expect(applyHeldPlanEmail(asked)).toBeNull();
	});

	it('does nothing with nothing held', () => {
		expect(applyHeldPlanEmail()).toBeNull();
		expect(schedules.set).not.toHaveBeenCalled();
	});

	it('remembers "Not now" per plan', () => {
		declinePlanEmail('humility');
		declinePlanEmail('humility');
		expect(planEmailDeclined('humility')).toBe(true);
		expect(planEmailDeclined('other-plan')).toBe(false);
		expect(JSON.parse(localStorage.getItem('ochorus:plan-email-declined')!)).toEqual(['humility']);
	});
});
