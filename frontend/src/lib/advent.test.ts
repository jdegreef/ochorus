import { describe, expect, it } from 'vitest';
import { adventFor, adventStatus, longDate, planWeeks, shortDate, statusLine } from './advent';

const on = (y: number, m: number, d: number) => new Date(y, m - 1, d, 12);

describe('adventFor', () => {
	it('is this year until Christmas Eve, then next year', () => {
		expect(adventFor(on(2026, 11, 11)).year).toBe(2026);
		expect(adventFor(on(2026, 12, 24)).year).toBe(2026);
		expect(adventFor(on(2026, 12, 25)).year).toBe(2027);
		expect(adventFor(on(2027, 1, 3)).year).toBe(2027);
	});

	it('runs from the fourth Sunday before Christmas to Christmas Eve', () => {
		const w = adventFor(on(2026, 11, 11));
		expect(longDate(w.start)).toBe('Sunday 29 November');
		expect(longDate(w.end)).toBe('Thursday 24 December');
		expect(longDate(adventFor(on(2027, 6, 1)).start)).toBe('Sunday 28 November');
		expect(longDate(adventFor(on(2023, 6, 1)).start)).toBe('Sunday 3 December');
	});
});

describe('adventStatus', () => {
	it('counts down before Advent', () => {
		expect(adventStatus(on(2026, 11, 11))).toEqual({ kind: 'before', days: 18 });
		expect(statusLine(on(2026, 11, 28))).toBe('Advent begins tomorrow, on Sunday 29 November.');
	});

	it('names the week inside Advent', () => {
		expect(adventStatus(on(2026, 11, 29))).toEqual({ kind: 'during', week: 1, daysToChristmas: 26 });
		expect(adventStatus(on(2026, 12, 6))).toMatchObject({ week: 2 });
		expect(statusLine(on(2026, 12, 24))).toBe('The fourth week of Advent · Christmas is tomorrow.');
	});

	it('points at next year from Christmas Day', () => {
		expect(statusLine(on(2026, 12, 25))).toBe('Advent begins in 338 days, on Sunday 28 November.');
	});
});

describe('planWeeks', () => {
	it('cuts the days into labelled sevens', () => {
		const days = Array.from({ length: 28 }, (_, i) => ({ day: i + 1 }));
		const weeks = planWeeks(days);
		expect(weeks.map((w) => w.days.length)).toEqual([7, 7, 7, 7]);
		expect(weeks[3].label).toBe('The Christmas story');
		expect(weeks[1].days[0].day).toBe(8);
	});
});

it('formats a short day', () => {
	expect(shortDate(adventFor(on(2026, 11, 11)).start)).toBe('Sun 29 Nov');
});
