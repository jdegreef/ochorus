import { flushSync, mount, unmount } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';

import WeekLamps from './WeekLamps.svelte';

/**
 * The week's lamps: lit on the days read, and a gold ring on the lamp whose
 * lighting met the week's goal — never on a day not yet come.
 */
let component: Record<string, unknown> | null = null;
let target: HTMLElement;
afterEach(() => {
	if (component) unmount(component);
	component = null;
	target?.remove();
});

// Wednesday 4 November 2026; the week runs Sunday 1 – Saturday 7.
const today = '2026-11-04';
function draw(days: string[], goal: number) {
	target = document.body.appendChild(document.createElement('div'));
	component = mount(WeekLamps, { target, props: { days, today, goal, locale: 'en' } }) as Record<string, unknown>;
	flushSync();
	const lamps = [...target.querySelectorAll<HTMLElement>('.lamp')];
	return {
		states: lamps.map((l) => l.dataset.state),
		ringed: lamps.flatMap((l, i) => (l.classList.contains('goal') ? [i] : [])),
		initials: lamps.map((l) => l.querySelector('.day')?.textContent).join('')
	};
}

describe('WeekLamps', () => {
	it('draws the week Sunday first, with its initials', () => {
		expect(draw([], 3).initials).toBe('SMTWTFS');
	});

	it('rings the lamp that met the goal', () => {
		const week = draw(['2026-11-01', '2026-11-02', '2026-11-04'], 3);
		expect(week.states).toEqual(['lit', 'lit', 'rest', 'lit', 'ahead', 'ahead', 'ahead']);
		expect(week.ringed).toEqual([3]);
	});

	it('rings nothing short of the goal, nor a day logged before it has come', () => {
		expect(draw(['2026-11-01', '2026-11-02', '2026-11-06'], 3).ringed).toEqual([]);
	});
});
