import { flushSync, mount, unmount } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * The daily reminder offered beside the plan page's Start button (design
 * review #24): the email switch signed in, the free-account ask signed out,
 * and the calendar view either way until the email is on.
 */
const auth = vi.hoisted(() => ({
	enabled: true,
	initialized: true,
	user: { email: 'grace@example.org' } as { email: string } | null
}));
vi.mock('$lib/auth.svelte', () => ({ auth }));
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
vi.mock('$lib/planSchedules.svelte', () => ({ planSchedules: schedules }));
const sheet = vi.hoisted(() => ({ show: vi.fn() }));
vi.mock('$lib/signInSheet.svelte', () => ({ signInSheet: sheet }));

const { default: PlanStartRemind } = await import('./PlanStartRemind.svelte');

let target: HTMLElement;
let component: ReturnType<typeof mount> | null = null;

function render() {
	component = mount(PlanStartRemind, { target, props: { slug: 'humility' } });
	flushSync();
}
const box = () => target.querySelector<HTMLInputElement>('input[type=checkbox]');
const calendar = () => target.querySelector<HTMLAnchorElement>('a[href*="view=calendar"]');

beforeEach(() => {
	localStorage.clear();
	auth.enabled = true;
	auth.user = { email: 'grace@example.org' };
	schedules.set.mockClear();
	sheet.show.mockClear();
	for (const k of Object.keys(schedules.store)) delete schedules.store[k];
	target = document.body.appendChild(document.createElement('div'));
});
afterEach(() => {
	if (component) unmount(component);
	component = null;
	target.remove();
});

describe('PlanStartRemind', () => {
	it('signed in: the switch turns the plan email on at the chosen time', () => {
		render();
		const time = target.querySelector<HTMLInputElement>('input[type=time]')!;
		time.value = '06:30';
		time.dispatchEvent(new Event('change', { bubbles: true }));
		flushSync();
		box()!.checked = true;
		box()!.dispatchEvent(new Event('change', { bubbles: true }));
		flushSync();
		expect(schedules.store.humility).toMatchObject({ email: true, time: '06:30' });
	});

	it('signed in with the email already on: the switch shows it, no calendar ask', () => {
		schedules.store.humility = { email: true, time: '07:00' };
		render();
		expect(box()!.checked).toBe(true);
		expect(calendar()).toBeNull();
	});

	it('signed out: asks for a free account and holds the choice', () => {
		auth.user = null;
		render();
		expect(box()).toBeNull();
		target.querySelector<HTMLButtonElement>('button')!.click();
		expect(sheet.show).toHaveBeenCalledWith('plan_start');
		expect(JSON.parse(localStorage.getItem('ochorus:plan-email-held')!)).toMatchObject({ slug: 'humility' });
		expect(calendar()).not.toBeNull();
	});

	it('without accounts at all, the calendar reminder is still offered', () => {
		auth.enabled = false;
		auth.user = null;
		render();
		expect(target.querySelector('button')).toBeNull();
		expect(calendar()?.getAttribute('href')).toContain('/plans/humility/?view=calendar');
	});
});
