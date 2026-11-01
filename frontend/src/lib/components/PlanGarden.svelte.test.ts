import { flushSync, mount, unmount } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';

import PlanGarden from './PlanGarden.svelte';

/**
 * The garden's one promise: it tells the reader's progress truly, and never
 * as a mark against them — a day read is a flower, today a sprout, everything
 * else (ahead, or skipped) a seed. A long plan shows the stretch around today.
 * The day the reader just marked read grows in; nothing else does.
 */
let component: Record<string, unknown> | null = null;
let target: HTMLElement;

type Props = { dayCount: number; done: Set<number>; next: number | null; grow?: number | null };

/** Mounts the garden over `props` (reactive when given a $state object). */
function plant(props: Props) {
	target = document.createElement('div');
	document.body.appendChild(target);
	component = mount(PlanGarden, {
		target,
		props: Object.assign(props, { hue: '#2f8f85', label: 'Plan: progress' })
	}) as Record<string, unknown>;
	flushSync();
}

const row = () =>
	[...target.querySelectorAll('svg.plant')]
		.map((p) => (p.querySelector('.bloom') ? 'F' : p.classList.contains('today') ? 'S' : 'o'))
		.join('');

function draw(props: Props): string {
	plant(props);
	return row();
}

/** The days (1-based, in the row) that are growing in. */
const growing = () =>
	[...target.querySelectorAll('svg.plant')].flatMap((p, i) => (p.classList.contains('grow') ? [i + 1] : []));

afterEach(() => {
	if (component) unmount(component);
	component = null;
	target?.remove();
});

describe('PlanGarden', () => {
	it('draws every day of a short plan: flowers read, a sprout today, seeds ahead and skipped', () => {
		expect(draw({ dayCount: 8, done: new Set([1, 2, 4]), next: 3 })).toBe('FFSFoooo');
		expect(target.querySelector('[role="img"]')?.getAttribute('aria-label')).toBe('Plan: progress');
	});

	it('shows 21 days around today on a long plan, with today in view', () => {
		const done = new Set(Array.from({ length: 40 }, (_, i) => i + 1));
		const row = draw({ dayCount: 90, done, next: 41 });
		expect(row).toHaveLength(21);
		expect(row).toMatch(/^F+So+$/);
	});

	it('ends the window on the last day once the plan is finished', () => {
		const done = new Set(Array.from({ length: 60 }, (_, i) => i + 1));
		expect(draw({ dayCount: 60, done, next: null })).toBe('F'.repeat(21));
	});
});

describe('PlanGarden growing', () => {
	it('grows the day just marked read and the sprout that comes up past it', () => {
		const props = $state<Props>({ dayCount: 6, done: new Set([1, 2]), next: 3 });
		plant(props);
		expect(growing()).toEqual([]);

		props.done = new Set([1, 2, 3]);
		props.next = 4;
		props.grow = 3;
		flushSync();
		expect(row()).toBe('FFFSoo');
		expect(growing()).toEqual([3, 4]);
	});

	it('draws progress that arrives without a tap (another tab, a sync) without growing it', () => {
		const props = $state<Props>({ dayCount: 6, done: new Set([1]), next: 2 });
		plant(props);
		props.done = new Set([1, 2, 3]);
		props.next = 4;
		flushSync();
		expect(row()).toBe('FFFSoo');
		expect(growing()).toEqual([]);
	});

	it('grows a later day ticked ahead, but not the sprout an earlier unread day keeps', () => {
		const props = $state<Props>({ dayCount: 6, done: new Set([1]), next: 2 });
		plant(props);
		props.done = new Set([1, 5]);
		props.grow = 5;
		flushSync();
		expect(row()).toBe('FSooFo');
		expect(growing()).toEqual([5]);
	});
});
