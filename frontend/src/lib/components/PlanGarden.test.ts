import { flushSync, mount, unmount } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';

import PlanGarden from './PlanGarden.svelte';

/**
 * The garden's one promise: it tells the reader's progress truly, and never
 * as a mark against them — a day read is a flower, today a sprout, everything
 * else (ahead, or skipped) a seed. A long plan shows the stretch around today.
 */
let component: Record<string, unknown> | null = null;
let target: HTMLElement;

function draw(props: { dayCount: number; done: Set<number>; next: number | null }): string {
	target = document.createElement('div');
	document.body.appendChild(target);
	component = mount(PlanGarden, { target, props: { ...props, hue: '#2f8f85', label: 'Plan: progress' } }) as Record<
		string,
		unknown
	>;
	flushSync();
	return [...target.querySelectorAll('svg.plant')]
		.map((p) => (p.querySelector('.bloom') ? 'F' : p.classList.contains('today') ? 'S' : 'o'))
		.join('');
}

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
