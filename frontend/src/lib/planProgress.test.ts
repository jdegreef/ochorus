import { beforeEach, describe, expect, it } from 'vitest';
import { completePlanDay, planProgress } from './planProgress.svelte';

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

	it('toggleDone flips a day and starts the plan on first mark', () => {
		expect(planProgress.isStarted('t')).toBe(false);
		planProgress.toggleDone('t', 2); // mark → also starts
		expect(planProgress.isStarted('t')).toBe(true);
		expect(planProgress.isDone('t', 2)).toBe(true);

		planProgress.toggleDone('t', 2); // unmark
		expect(planProgress.isDone('t', 2)).toBe(false);
		expect(planProgress.doneDays('t')).toEqual([]);
	});

	it('unmarkDone is a no-op for an unmarked day', () => {
		planProgress.markDone('u', 1);
		planProgress.unmarkDone('u', 5); // never marked
		expect(planProgress.doneDays('u')).toEqual([1]);
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

describe('completePlanDay', () => {
	const plan = {
		slug: 'year',
		day_count: 3,
		days: [1, 2, 3].map((day) => ({
			day,
			book_slug: 'days-of-heaven-upon-earth',
			chapter_order: 1,
			entry_date: `01-0${day}`,
			book_title: '',
			chapter_title: '',
			word_count: 0
		}))
	};

	it('marks the day and goes on to the next undone one', () => {
		expect(completePlanDay(plan, 1)).toBe('/today/days-of-heaven-upon-earth/?d=01-02&plan=year&day=2');
		expect(planProgress.isDone('year', 1)).toBe(true);
		planProgress.markDone('year', 2);
		// Day 2 is already done, so finishing day 3 skips nothing: back to the plan.
		expect(completePlanDay(plan, 3)).toBe('/plans/year');
	});
});
