import { describe, expect, it } from 'vitest';
import { adventStart, easterDay, liturgicalSeason } from './liturgical';

const day = (y: number, m: number, d: number) => Date.UTC(y, m - 1, d) / 86_400_000;
const on = (y: number, m: number, d: number) => liturgicalSeason(new Date(y, m - 1, d));

describe('easterDay', () => {
	it.each([
		[2024, 3, 31],
		[2025, 4, 20],
		[2026, 4, 5],
		[2027, 3, 28],
		[2038, 4, 25],
		[2285, 3, 22]
	])('Easter %i is %i/%i', (y, m, d) => {
		expect(easterDay(y)).toBe(day(y, m, d));
	});
});

describe('adventStart', () => {
	it.each([
		[2023, 12, 3],
		[2024, 12, 1],
		[2025, 11, 30],
		[2026, 11, 29],
		[2022, 11, 27]
	])('Advent %i begins %i/%i', (y, m, d) => {
		expect(adventStart(y)).toBe(day(y, m, d));
	});
});

describe('liturgicalSeason', () => {
	it('walks the 2026 year across every boundary', () => {
		expect(on(2026, 1, 1)).toBe('christmas');
		expect(on(2026, 1, 5)).toBe('christmas');
		expect(on(2026, 1, 6)).toBe('epiphany');
		expect(on(2026, 1, 7)).toBe('ordinary');
		expect(on(2026, 2, 17)).toBe('ordinary'); // Shrove Tuesday
		expect(on(2026, 2, 18)).toBe('lent'); // Ash Wednesday
		expect(on(2026, 3, 28)).toBe('lent');
		expect(on(2026, 3, 29)).toBe('holyWeek'); // Palm Sunday
		expect(on(2026, 4, 4)).toBe('holyWeek'); // Holy Saturday
		expect(on(2026, 4, 5)).toBe('easter');
		expect(on(2026, 5, 23)).toBe('easter');
		expect(on(2026, 5, 24)).toBe('pentecost');
		expect(on(2026, 5, 25)).toBe('ordinary');
		expect(on(2026, 10, 6)).toBe('ordinary');
		expect(on(2026, 11, 28)).toBe('ordinary');
		expect(on(2026, 11, 29)).toBe('advent');
		expect(on(2026, 12, 24)).toBe('advent');
		expect(on(2026, 12, 25)).toBe('christmas');
		expect(on(2026, 12, 31)).toBe('christmas');
	});

	it('reads the local calendar day, not the UTC one', () => {
		// 23:30 local on Christmas Eve is still Advent wherever the reader is.
		expect(liturgicalSeason(new Date(2026, 11, 24, 23, 30))).toBe('advent');
	});
});
