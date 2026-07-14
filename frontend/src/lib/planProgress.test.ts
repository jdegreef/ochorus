import { beforeEach, describe, expect, it } from 'vitest';
import { planProgress } from './planProgress.svelte';

beforeEach(() => localStorage.clear());

describe('planProgress store', () => {
	it('starts a plan once and reports it started', () => {
		expect(planProgress.isStarted('humility')).toBe(false);
		planProgress.start('humility');
		expect(planProgress.isStarted('humility')).toBe(true);

		const before = planProgress.doneDays('humility');
		planProgress.start('humility'); // idempotent — must not wipe progress
		expect(planProgress.doneDays('humility')).toEqual(before);
	});

	it('marks days done without duplicates and keeps them sorted', () => {
		planProgress.markDone('humility', 3);
		planProgress.markDone('humility', 1);
		planProgress.markDone('humility', 3); // duplicate
		expect(planProgress.doneDays('humility')).toEqual([1, 3]);
		expect(planProgress.isDone('humility', 1)).toBe(true);
		expect(planProgress.isDone('humility', 2)).toBe(false);
	});

	it('nextDay returns the first uncompleted day, or null when finished', () => {
		planProgress.markDone('p', 1);
		planProgress.markDone('p', 2);
		expect(planProgress.nextDay('p', 3)).toBe(3);

		planProgress.markDone('p', 3);
		expect(planProgress.nextDay('p', 3)).toBeNull();
	});

	it('lists started plans with their completed-day counts', () => {
		planProgress.start('a');
		planProgress.markDone('b', 1);
		planProgress.markDone('b', 2);
		const started = planProgress.started();
		expect(new Set(started.map((s) => s.slug))).toEqual(new Set(['a', 'b']));
		expect(started.find((s) => s.slug === 'b')?.doneCount).toBe(2);
	});
});
