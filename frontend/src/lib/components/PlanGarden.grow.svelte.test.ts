import { flushSync, mount, unmount } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';

import PlanGarden from './PlanGarden.svelte';

/**
 * The garden grows in front of the reader: a day marked read while it is on
 * screen comes into flower, and the next day's sprout comes up after it. The
 * garden as it stood on arrival is simply drawn, so a visit never replays.
 */
let component: Record<string, unknown> | null = null;
let target: HTMLElement;

afterEach(() => {
	if (component) unmount(component);
	component = null;
	target?.remove();
});

const growing = () =>
	[...target.querySelectorAll('svg.plant')].map((p, i) => (p.classList.contains('grow') ? i + 1 : 0)).filter(Boolean);

describe('PlanGarden growing', () => {
	it('draws the garden it arrives to without growing anything', () => {
		const props = $state({ dayCount: 6, done: new Set([1, 2]), next: 3 as number | null, hue: '#2f8f85', label: 'Plan' });
		target = document.body.appendChild(document.createElement('div'));
		component = mount(PlanGarden, { target, props }) as Record<string, unknown>;
		flushSync();
		expect(growing()).toEqual([]);
	});

	it('grows the day just marked read and the sprout that comes up after it', () => {
		const props = $state({ dayCount: 6, done: new Set([1, 2]), next: 3 as number | null, hue: '#2f8f85', label: 'Plan' });
		target = document.body.appendChild(document.createElement('div'));
		component = mount(PlanGarden, { target, props }) as Record<string, unknown>;
		flushSync();

		props.done = new Set([1, 2, 3]);
		props.next = 4;
		flushSync();
		expect(growing()).toEqual([3, 4]);
		expect(target.querySelectorAll('svg.plant')[2].querySelector('.bloom')).not.toBeNull();
		expect(target.querySelectorAll('svg.plant')[3].classList.contains('today')).toBe(true);

		// The last day read: its flower grows, and there is no sprout left to come up.
		props.done = new Set([1, 2, 3, 4, 5, 6]);
		props.next = null;
		flushSync();
		expect(growing()).toEqual([3, 4, 5, 6]);
	});
});
