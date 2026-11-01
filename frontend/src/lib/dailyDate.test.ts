import { describe, expect, it } from 'vitest';
import { dateKey, inputValue, isDateKey } from './dailyDate';

describe('dailyDate', () => {
	it('keys a date by its LOCAL month and day', () => {
		expect(dateKey(new Date(2026, 9, 30, 23, 59))).toBe('10-30');
		expect(dateKey(new Date(2026, 0, 1, 0, 0))).toBe('01-01');
	});

	it('accepts only real calendar dates, 29 February included', () => {
		for (const ok of ['01-01', '02-29', '12-31', '04-30']) expect(isDateKey(ok)).toBe(true);
		for (const bad of ['02-30', '04-31', '13-01', '00-10', '1-01', 'today', '', null, undefined])
			expect(isDateKey(bad)).toBe(false);
	});

	it('gives a date input this year, or a leap year for 29 February', () => {
		expect(inputValue('10-30', new Date(2026, 5, 1))).toBe('2026-10-30');
		expect(inputValue('02-29', new Date(2026, 5, 1))).toBe('2024-02-29');
		expect(inputValue('02-29', new Date(2028, 5, 1))).toBe('2028-02-29');
	});
});
