import { createRawSnippet, flushSync, mount, unmount } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * The end-of-plan-day email switch, for signed-in readers.
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
vi.mock('$lib/signInSheet.svelte', () => ({ signInSheet: { show: vi.fn() } }));

const { default: PlanDayRemind } = await import('./PlanDayRemind.svelte');

const otherwise = createRawSnippet(() => ({ render: () => '<p class="otherwise">usual card</p>' }));
let target: HTMLElement;
let component: ReturnType<typeof mount> | null = null;

function render(props: { day?: number; dayCount?: number } = {}) {
	component = mount(PlanDayRemind, {
		target,
		props: { slug: 'humility', day: props.day ?? 3, dayCount: props.dayCount ?? 12, otherwise }
	});
	flushSync();
}
const card = () => target.querySelector('aside');
const box = () => target.querySelector<HTMLInputElement>('aside input[type=checkbox]')!;
const tick = (el: HTMLInputElement, checked: boolean) => {
	el.checked = checked;
	el.dispatchEvent(new Event('change', { bubbles: true }));
	flushSync();
};

beforeEach(() => {
	localStorage.clear();
	auth.user = { email: 'grace@example.org' };
	schedules.set.mockClear();
	for (const k of Object.keys(schedules.store)) delete schedules.store[k];
	target = document.body.appendChild(document.createElement('div'));
});
afterEach(() => {
	if (component) unmount(component);
	component = null;
	target.remove();
});

describe('PlanDayRemind', () => {
	it('ticking the switch turns the plan email on, and the ticked switch stays', () => {
		render();
		expect(box().checked).toBe(false);
		tick(box(), true);
		expect(schedules.store.humility).toMatchObject({ email: true, time: '07:00' });
		expect(card()).not.toBeNull();
		expect(box().checked).toBe(true);
		// …and off again from the same place.
		tick(box(), false);
		expect(schedules.store.humility).toMatchObject({ email: false });
	});

	it('"Not now" works after the switch has been tried on and off', () => {
		render();
		tick(box(), true);
		tick(box(), false);
		target.querySelector<HTMLButtonElement>('aside button')!.click();
		flushSync();
		expect(card()).toBeNull();
	});

	it('keeps the last time when the time field is cleared', () => {
		render();
		tick(box(), true);
		const input = target.querySelector<HTMLInputElement>('input[type=time]')!;
		input.value = '';
		input.dispatchEvent(new Event('change', { bubbles: true }));
		flushSync();
		expect(schedules.store.humility).toMatchObject({ time: '07:00' });
	});

	it('starts from the time the plan already has', () => {
		schedules.store.humility = { time: '06:15' };
		render();
		expect(target.querySelector<HTMLInputElement>('input[type=time]')!.value).toBe('06:15');
	});

	it('leaves signed-out readers to the usual card', () => {
		auth.user = null;
		render();
		expect(card()).toBeNull();
		expect(target.querySelector('.otherwise')).not.toBeNull();
	});

	it('shows the usual card on the last day: there is no tomorrow to send', () => {
		render({ day: 12, dayCount: 12 });
		expect(card()).toBeNull();
		expect(target.querySelector('.otherwise')).not.toBeNull();
	});

	it('shows the usual card when the plan already emails the reader', () => {
		schedules.store.humility = { email: true, time: '06:00' };
		render();
		expect(card()).toBeNull();
		expect(target.querySelector('.otherwise')).not.toBeNull();
	});

	it('"Not now" stops this plan offering it', () => {
		render();
		target.querySelector<HTMLButtonElement>('aside button')!.click();
		flushSync();
		expect(card()).toBeNull();
		unmount(component!);
		render();
		expect(card()).toBeNull();
		expect(target.querySelector('.otherwise')).not.toBeNull();
	});
});
