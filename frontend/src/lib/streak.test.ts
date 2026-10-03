import { describe, it, expect } from 'vitest';
import { shiftDay, localToday, currentStreak, longestStreak, streakTier, runLengths, runLevel } from './streak';

describe('streak maths', () => {
	it('shiftDay crosses month and year boundaries', () => {
		expect(shiftDay('2026-03-01', -1)).toBe('2026-02-28');
		expect(shiftDay('2026-01-01', -1)).toBe('2025-12-31');
		expect(shiftDay('2026-07-20', 3)).toBe('2026-07-23');
	});

	it('localToday formats the local date', () => {
		expect(localToday(new Date('2026-07-05T09:00:00'))).toBe('2026-07-05');
	});

	const run = ['2026-07-20', '2026-07-21', '2026-07-22'];

	it('counts a run ending today', () => {
		expect(currentStreak(run, '2026-07-22')).toBe(3);
	});

	it("keeps the streak while today isn't read yet (ends yesterday)", () => {
		expect(currentStreak(run, '2026-07-23')).toBe(3);
	});

	it('breaks after a full day passes unread', () => {
		expect(currentStreak(run, '2026-07-24')).toBe(0);
	});

	it('is zero for an empty log', () => {
		expect(currentStreak([], '2026-07-22')).toBe(0);
	});

	it('ignores duplicates and finds the longest run', () => {
		const days = ['2026-07-01', '2026-07-01', '2026-07-02', '2026-07-03', '2026-07-06', '2026-07-07'];
		expect(longestStreak(days)).toBe(3);
	});
});

describe('streakTier', () => {
	it('steps spark, flame, blaze, crown at 7, 30 and 100 days', () => {
		expect([0, 6, 7, 29, 30, 99, 100, 365].map(streakTier)).toEqual([
			'spark', 'spark', 'flame', 'flame', 'blaze', 'blaze', 'crown', 'crown'
		]);
	});
});

describe('runLengths / runLevel', () => {
	it('numbers each day by its place in its unbroken run', () => {
		const runs = runLengths(['2026-07-01', '2026-07-02', '2026-07-03', '2026-07-05', '2026-07-02']);
		expect(runs.get('2026-07-03')).toBe(3);
		// A gap restarts the count; a duplicate log entry changes nothing.
		expect(runs.get('2026-07-05')).toBe(1);
		expect(runs.size).toBe(4);
	});

	it('runs across a month boundary, and skips malformed entries', () => {
		expect(runLengths(['2026-06-30', '', 'x', '2026-7-1', '2026-07-01']).get('2026-07-01')).toBe(2);
		expect(longestStreak(['', '2026-06-30', '2026-07-01'])).toBe(2);
	});

	it('shades a run by the same steps as the flame', () => {
		expect([0, 1, 6, 7, 29, 30, 99, 100].map(runLevel)).toEqual([0, 1, 1, 2, 2, 3, 3, 4]);
	});
});
