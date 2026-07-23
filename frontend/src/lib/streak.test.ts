import { describe, it, expect } from 'vitest';
import { shiftDay, localToday, currentStreak, longestStreak } from './streak';

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
