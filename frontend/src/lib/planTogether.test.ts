import { describe, expect, it } from 'vitest';
import { countedDay, groupStatus, nextMonday, togetherFromQuery, togetherQuery } from './planTogether';
import { localToday } from './streak';

const day = (iso: string) => {
	const [y, m, d] = iso.split('-').map(Number);
	return new Date(y, m - 1, d);
};

describe('read-together links', () => {
	it('round-trips a group through its query string', () => {
		const t = { start: '2026-10-12', rule: 'weekdays' as const };
		expect(togetherQuery(t)).toBe('?together=2026-10-12&days=weekdays');
		expect(togetherFromQuery(new URLSearchParams(togetherQuery(t)))).toEqual(t);
	});

	it('leaves the default rule out of the link, and reads its absence as daily', () => {
		expect(togetherQuery({ start: '2026-10-12', rule: 'daily' })).toBe('?together=2026-10-12');
		expect(togetherFromQuery(new URLSearchParams('together=2026-10-12'))).toEqual({ start: '2026-10-12', rule: 'daily' });
	});

	it('carries a group code when its totals are on, and drops a malformed one', () => {
		const t = { start: '2026-10-12', rule: 'daily' as const, group: 'KunYdx4NiTLQ' };
		expect(togetherQuery(t)).toBe('?together=2026-10-12&group=KunYdx4NiTLQ');
		expect(togetherFromQuery(new URLSearchParams(togetherQuery(t)))).toEqual(t);
		expect(togetherFromQuery(new URLSearchParams('together=2026-10-12&group=<x>'))).toEqual({
			start: '2026-10-12',
			rule: 'daily'
		});
	});

	it('ignores a link with no group or a malformed date, and an unknown rule', () => {
		expect(togetherFromQuery(new URLSearchParams(''))).toBeNull();
		expect(togetherFromQuery(new URLSearchParams('together=2026-02-30'))).toBeNull();
		expect(togetherFromQuery(new URLSearchParams('together=next-week'))).toBeNull();
		expect(togetherFromQuery(new URLSearchParams('together=2026-10-12&days=sometimes'))?.rule).toBe('daily');
	});
});

describe('where the group is', () => {
	// Monday 12 October 2026, five days, weekdays only: Mon 12 … Fri 16.
	const t = { start: '2026-10-12', rule: 'weekdays' as const };

	it('counts down before the start', () => {
		const s = groupStatus(t, 5, day('2026-10-09'));
		expect(s.kind).toBe('before');
		expect(s.kind === 'before' && localToday(s.starts)).toBe('2026-10-12');
	});

	it('names the day of the plan on a reading day', () => {
		expect(groupStatus(t, 5, day('2026-10-12'))).toEqual({ kind: 'today', day: 1 });
		expect(groupStatus(t, 5, day('2026-10-15'))).toEqual({ kind: 'today', day: 4 });
	});

	it('points to the next reading on a day the group rests', () => {
		// A weekdays group that started on a Saturday reads first on Monday.
		const s = groupStatus({ start: '2026-10-10', rule: 'weekdays' }, 5, day('2026-10-11'));
		expect(s.kind).toBe('before');
		// Mid-plan rest day: Saturday 17th, after Friday's day 5 of a 6-day plan.
		const mid = groupStatus(t, 6, day('2026-10-17'));
		expect(mid.kind === 'next' && mid.day).toBe(6);
		expect(mid.kind === 'next' && localToday(mid.date)).toBe('2026-10-19');
	});

	it('reports a finished plan', () => {
		const s = groupStatus(t, 5, day('2026-10-17'));
		expect(s.kind).toBe('finished');
		expect(s.kind === 'finished' && localToday(s.ended)).toBe('2026-10-16');
	});
});

describe('the day a group counts', () => {
	it("is today's reading, the last one on a rest day, the plan's last once finished, none before", () => {
		expect(countedDay({ kind: 'today', day: 4 }, 12)).toBe(4);
		expect(countedDay({ kind: 'next', day: 6, date: new Date() }, 12)).toBe(5);
		expect(countedDay({ kind: 'next', day: 1, date: new Date() }, 12)).toBeNull();
		expect(countedDay({ kind: 'finished', ended: new Date() }, 12)).toBe(12);
		expect(countedDay({ kind: 'before', starts: new Date() }, 12)).toBeNull();
	});
});

describe('the offered start', () => {
	it('is the coming Monday, or today when today is one', () => {
		expect(nextMonday(day('2026-10-12'))).toBe('2026-10-12'); // Monday
		expect(nextMonday(day('2026-10-13'))).toBe('2026-10-19'); // Tuesday
		expect(nextMonday(day('2026-10-18'))).toBe('2026-10-19'); // Sunday
	});
});
