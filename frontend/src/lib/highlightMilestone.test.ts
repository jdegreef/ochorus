import { beforeEach, describe, expect, it } from 'vitest';
import { lastMilestone, milestoneFor, milestonesDone, recordMilestone } from './highlightMilestone';

beforeEach(() => localStorage.clear());

describe('milestoneFor', () => {
	it('announces 3, 10 and 25, each once', () => {
		expect(milestoneFor(2, 0)).toBeNull();
		expect(milestoneFor(3, 0)).toBe(3);
		expect(milestoneFor(3, 3)).toBeNull();
		expect(milestoneFor(9, 3)).toBeNull();
		expect(milestoneFor(10, 3)).toBe(10);
		expect(milestoneFor(25, 10)).toBe(25);
	});

	it('still announces a milestone the count jumped past (the highest one)', () => {
		expect(milestoneFor(12, 0)).toBe(10);
		expect(milestoneFor(40, 3)).toBe(25);
	});

	it('does not repeat after the count dips and recovers', () => {
		expect(milestoneFor(3, 3)).toBeNull();
	});
});

describe('stored last milestone', () => {
	it('round-trips, and knows when all are done', () => {
		expect(lastMilestone()).toBe(0);
		recordMilestone(10);
		expect(lastMilestone()).toBe(10);
		expect(milestonesDone(10)).toBe(false);
		expect(milestonesDone(25)).toBe(true);
	});
});
