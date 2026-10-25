import { flushSync, mount, unmount } from 'svelte';
import { readable } from 'svelte/store';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * The end-of-chapter card for signed-out readers, and its plan-day variant:
 * the plan's daily email, held while the sign-up panel opens.
 */
vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://ochorus.test/books/humility/3/?plan=humility&day=3') })
}));
vi.mock('$lib/auth.svelte', () => ({ auth: { enabled: true, initialized: true, user: null } }));
const schedules = vi.hoisted(() => {
	const store: Record<string, Record<string, unknown>> = {};
	return { store, get: (slug: string) => store[slug] ?? {}, set: vi.fn() };
});
vi.mock('$lib/planSchedules.svelte', () => ({ planSchedules: schedules }));
const askForPlanEmail = vi.hoisted(() => vi.fn());
const declinePlanEmail = vi.hoisted(() => vi.fn());
const planEmailDeclined = vi.hoisted(() => vi.fn(() => false));
vi.mock('$lib/planEmail', () => ({ askForPlanEmail, declinePlanEmail, planEmailDeclined }));

const { default: ChapterEndAsk } = await import('./ChapterEndAsk.svelte');
const { snoozeAsk } = await import('$lib/chapterAsk');

// jsdom has no layout: report the chapter end as reached at once.
beforeAll(() => {
	vi.stubGlobal(
		'IntersectionObserver',
		class {
			constructor(private cb: (e: { isIntersecting: boolean }[]) => void) {}
			observe() {
				this.cb([{ isIntersecting: true }]);
			}
			disconnect() {}
		}
	);
});
afterAll(() => vi.unstubAllGlobals());

let target: HTMLElement;
let component: ReturnType<typeof mount> | null = null;
function render(planSlug?: string) {
	component = mount(ChapterEndAsk, {
		target,
		props: { title: 'Humility', chapterKey: 'book:humility:3', planSlug }
	});
	flushSync();
}

beforeEach(() => {
	localStorage.clear();
	askForPlanEmail.mockClear();
	declinePlanEmail.mockClear();
	planEmailDeclined.mockReturnValue(false);
	for (const k of Object.keys(schedules.store)) delete schedules.store[k];
	target = document.body.appendChild(document.createElement('div'));
});
afterEach(() => {
	if (component) unmount(component);
	component = null;
	target.remove();
});

describe('ChapterEndAsk', () => {
	it('asks for an account at the end of a chapter', () => {
		render();
		const cta = target.querySelector<HTMLAnchorElement>('aside a.btn-primary')!;
		expect(cta.href).toContain('src=chapter_end');
	});

	it('on a plan day, offers the plan email and holds it for the sign-up', () => {
		render('humility');
		const offer = target.querySelector<HTMLAnchorElement>('aside a.btn-primary')!;
		expect(offer.href).toContain('src=plan_day');
		offer.click();
		expect(askForPlanEmail).toHaveBeenCalledWith('humility', 'plan_day');
	});

	it("offers a plan's reminder even while the account ask is snoozed", () => {
		// Day 1's end is where a plan's reminder is offered at all.
		snoozeAsk();
		render('humility');
		expect(target.querySelector('aside a.btn-primary')?.getAttribute('href')).toContain('src=plan_day');
	});

	it('offers a calendar reminder too, which needs no account', () => {
		render('humility');
		const calendar = target.querySelector<HTMLAnchorElement>('aside a.btn-ghost')!;
		expect(calendar.getAttribute('href')).toContain('/plans/humility/?view=calendar');
	});

	it('"Not now" on a plan offer stops that plan offering, not the account ask', () => {
		render('humility');
		target.querySelector<HTMLButtonElement>('aside button')!.click();
		flushSync();
		expect(declinePlanEmail).toHaveBeenCalledWith('humility');
		expect(localStorage.getItem('ochorus:chapter_ask')).toBeNull();
		expect(target.querySelector('aside')).toBeNull();
	});

	it('leaves a declined plan to the account ask', () => {
		planEmailDeclined.mockReturnValue(true);
		render('humility');
		expect(target.querySelector('aside a.btn-primary')?.getAttribute('href')).toContain('src=chapter_end');
	});

	it('a modified click on the plan offer follows the real /login link instead', () => {
		render('humility');
		const offer = target.querySelector<HTMLAnchorElement>('aside a.btn-primary')!;
		const click = new MouseEvent('click', { bubbles: true, cancelable: true, metaKey: true });
		offer.dispatchEvent(click);
		expect(askForPlanEmail).not.toHaveBeenCalled();
		expect(click.defaultPrevented).toBe(false);
	});

	it('falls back to the account ask when the plan already emails', () => {
		schedules.store.humility = { email: true };
		render('humility');
		expect(target.querySelector<HTMLAnchorElement>('aside a.btn-primary')!.href).toContain('src=chapter_end');
	});
});
