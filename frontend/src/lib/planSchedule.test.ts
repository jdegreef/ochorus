import { describe, expect, it } from 'vitest';
import { monthGrid, parseIsoDay, readsOn, schedulePlan, weekStart } from './planSchedule';
import { localToday as isoDay } from './streak';
import { buildScheduleICS } from './reminder';

// Mon 5 Oct 2026.
const MON = new Date(2026, 9, 5);

describe('schedulePlan', () => {
	it('puts one day on each reading day from the start', () => {
		const s = schedulePlan([1, 2, 3], MON, 'daily');
		expect(s.map((x) => [x.item, isoDay(x.date)])).toEqual([
			[1, '2026-10-05'],
			[2, '2026-10-06'],
			[3, '2026-10-07']
		]);
	});

	it('skips the days a reader does not read on', () => {
		const fri = new Date(2026, 9, 9);
		expect(schedulePlan([7, 8], fri, 'weekdays').map((x) => isoDay(x.date))).toEqual([
			'2026-10-09',
			'2026-10-12'
		]);
		expect(schedulePlan([7, 8], fri, 'monsat').map((x) => isoDay(x.date))).toEqual([
			'2026-10-09',
			'2026-10-10'
		]);
		// A Sunday start on weekdays begins on Monday.
		expect(isoDay(schedulePlan([1], new Date(2026, 9, 4), 'weekdays')[0].date)).toBe('2026-10-05');
	});

	it('finishes a 96-day plan read daily from 5 Oct on 8 Jan', () => {
		const s = schedulePlan(Array.from({ length: 96 }, (_, i) => i + 1), MON, 'daily');
		expect(isoDay(s[95].date)).toBe('2027-01-08');
	});
});

describe('readsOn / parseIsoDay', () => {
	it('knows the weekday rules', () => {
		const sun = new Date(2026, 9, 4);
		expect([readsOn(sun, 'daily'), readsOn(sun, 'weekdays'), readsOn(sun, 'monsat')]).toEqual([true, false, false]);
	});

	it('round-trips a date and rejects anything else', () => {
		expect(isoDay(parseIsoDay('2026-10-05')!)).toBe('2026-10-05');
		expect(parseIsoDay('2026-02-30')).toBeNull();
		expect(parseIsoDay('')).toBeNull();
	});
});

describe('monthGrid', () => {
	it('lays October 2026 out Monday-first in whole weeks', () => {
		const g = monthGrid(2026, 9);
		expect(g.every((w) => w.length === 7)).toBe(true);
		expect(g[0][0].iso).toBe('2026-09-28'); // Oct 1 is a Thursday
		expect(g.at(-1)!.at(-1)!.iso).toBe('2026-11-01');
	});

	it('starts its weeks on the day it is given (Sunday for en-US)', () => {
		const g = monthGrid(2026, 9, 0);
		expect(g[0][0].iso).toBe('2026-09-27');
		expect(g[0].map((d) => d.date.getDay())).toEqual([0, 1, 2, 3, 4, 5, 6]);
	});
});

describe('weekStart', () => {
	it('is a weekday number, Monday when the locale cannot say', () => {
		expect(weekStart('not a tag!!')).toBe(1);
		expect([0, 1, 6]).toContain(weekStart('en-US'));
	});
});

describe('buildScheduleICS', () => {
	it('writes one all-day event per reading with a morning alert', () => {
		const ics = buildScheduleICS(
			[
				{ date: MON, summary: 'Day 1 · Called by Name', url: 'https://ochorus.com/x' },
				{ date: new Date(2026, 9, 6), summary: 'Day 2, Made; to Reflect', url: 'https://ochorus.com/y' }
			],
			'07:30',
			{ now: MON, uidPrefix: 'plan-dotk' }
		);
		expect(ics.match(/BEGIN:VEVENT/g)).toHaveLength(2);
		expect(ics).toContain('DTSTART;VALUE=DATE:20261005');
		expect(ics).not.toContain('DTEND');
		expect(ics).toContain('TRIGGER:PT7H30M');
		expect(ics).toContain(String.raw`SUMMARY:Day 2\, Made\; to Reflect`);
		expect(ics).toContain('UID:plan-dotk-2');
		expect(ics.endsWith('END:VCALENDAR\r\n')).toBe(true);
	});
});
