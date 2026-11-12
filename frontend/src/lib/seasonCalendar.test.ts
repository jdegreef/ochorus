import { describe, expect, it } from 'vitest';
import {
	ADVENT_DOORS,
	adventWindow,
	doorState,
	enoughDoors,
	fitEntries,
	lentWindow,
	resolveDoors,
	seasonWindowOn,
	type CalendarEntry,
	type Shelf
} from './seasonCalendar';

const on = (y: number, m: number, d: number) => new Date(y, m - 1, d, 12);
const iso = (n: number) => new Date(n * 86_400_000).toISOString().slice(0, 10);
const weekday = (n: number) => new Date(n * 86_400_000).getUTCDay();

describe('adventWindow', () => {
	it('runs from Advent Sunday to Christmas Eve, a door a day', () => {
		const cases: [number, string, number][] = [
			[2022, '2022-11-27', 28], // Christmas on a Sunday: the longest Advent
			[2023, '2023-12-03', 22], // Christmas on a Monday: the shortest
			[2024, '2024-12-01', 24],
			[2025, '2025-11-30', 25],
			[2026, '2026-11-29', 26],
			[2027, '2027-11-28', 27]
		];
		for (const [year, start, length] of cases) {
			const w = adventWindow(year);
			expect(iso(w.days[0]), String(year)).toBe(start);
			expect(weekday(w.days[0])).toBe(0);
			expect(iso(w.days[w.days.length - 1])).toBe(`${year}-12-24`);
			expect(w.days).toHaveLength(length);
		}
	});
});

describe('lentWindow', () => {
	it('runs from Ash Wednesday to Holy Saturday: forty days without the Sundays', () => {
		// Easter: 31 Mar 2024, 20 Apr 2025, 5 Apr 2026, 28 Mar 2027.
		const cases: [number, string, string][] = [
			[2024, '2024-02-14', '2024-03-30'],
			[2025, '2025-03-05', '2025-04-19'],
			[2026, '2026-02-18', '2026-04-04'],
			[2027, '2027-02-10', '2027-03-27']
		];
		for (const [year, ash, holySat] of cases) {
			const w = lentWindow(year);
			expect(iso(w.days[0]), String(year)).toBe(ash);
			expect(weekday(w.days[0])).toBe(3);
			expect(iso(w.days[w.days.length - 1])).toBe(holySat);
			expect(w.days).toHaveLength(40);
			expect(w.days.some((d) => weekday(d) === 0)).toBe(false);
		}
	});
});

describe('seasonWindowOn', () => {
	it('finds the season the local date is in, and nothing between', () => {
		expect(seasonWindowOn(on(2026, 11, 28))).toBeNull();
		expect(seasonWindowOn(on(2026, 11, 29))?.season).toBe('advent');
		expect(seasonWindowOn(on(2026, 12, 24))?.season).toBe('advent');
		expect(seasonWindowOn(on(2026, 12, 25))).toBeNull();
		expect(seasonWindowOn(on(2027, 2, 9))).toBeNull();
		expect(seasonWindowOn(on(2027, 2, 10))?.season).toBe('lent');
		// A Sunday in Lent is inside the season, though it has no door.
		expect(seasonWindowOn(on(2027, 2, 14))?.season).toBe('lent');
		expect(seasonWindowOn(on(2027, 3, 27))?.season).toBe('lent');
		expect(seasonWindowOn(on(2027, 3, 28))).toBeNull();
	});

	it('reads the local calendar day, not UTC', () => {
		// 23:30 on Advent Eve, local: still before the season wherever the reader is.
		expect(seasonWindowOn(new Date(2026, 10, 28, 23, 30))).toBeNull();
		expect(seasonWindowOn(new Date(2026, 10, 29, 0, 30))?.season).toBe('advent');
	});
});

describe('the Advent list', () => {
	const key = (e: CalendarEntry) =>
		e.reading.kind === 'sermon' ? e.reading.slug : `${e.reading.book}/${e.reading.chapter}`;

	it('is written for the longest Advent, with spares enough for the shortest', () => {
		expect(ADVENT_DOORS).toHaveLength(28);
		expect(ADVENT_DOORS.filter((e) => e.spare).length).toBeGreaterThanOrEqual(28 - 22);
		expect(new Set(ADVENT_DOORS.map(key)).size).toBe(ADVENT_DOORS.length);
	});

	it('fits every Advent, opening on the coming and closing on the birth', () => {
		for (let year = 2000; year <= 2100; year++) {
			const w = adventWindow(year);
			const fitted = fitEntries(ADVENT_DOORS, w.days.length);
			expect(fitted, String(year)).toHaveLength(w.days.length);
			expect(key(fitted[0])).toBe('waiting-on-god/30');
			expect(key(fitted[fitted.length - 1])).toBe('the-story-of-the-birth-of-jesus');
		}
	});

	it('drops spares from the end first', () => {
		const fitted = fitEntries(ADVENT_DOORS, 26).map(key);
		expect(fitted).not.toContain('the-mystery-of-godliness');
		expect(fitted).not.toContain('the-heavenly-workers-and-the-earthly-watchers');
		expect(fitted).toContain('brave-encouragements');
	});
});

describe('doorState', () => {
	it('opens the past, lights today, locks the rest', () => {
		expect(doorState(10, 11)).toBe('open');
		expect(doorState(11, 11)).toBe('today');
		expect(doorState(12, 11)).toBe('locked');
	});
});

describe('resolveDoors', () => {
	const entries: CalendarEntry[] = [
		{ reading: { kind: 'sermon', slug: 'unto-us' } },
		{ reading: { kind: 'chapter', book: 'waiting', chapter: 30, ref: 'Luke 12:36' } },
		{ reading: { kind: 'sermon', slug: 'english-only' } },
		{ reading: { kind: 'chapter', book: 'waiting', chapter: 99, ref: 'Psalm 1:1' } }
	];
	const w = { season: 'advent' as const, year: 2026, days: [100, 101, 102, 103] };
	const shelf = (lang: string): Shelf => ({
		sermons: new Map([
			['unto-us', { title: lang === 'fr' ? 'Un enfant nous est né' : 'Unto Us', scripture_ref: lang === 'fr' ? 'Ésaïe 9:5' : 'Isaiah 9:6' }],
			...(lang === 'en' ? [['english-only', { title: 'Only English', scripture_ref: 'John 1:14' }] as const] : [])
		]),
		books: new Map([['waiting', { title: 'Waiting', chapters: [{ order: 30, title: 'Ch 30' }] }]])
	});

	it('dates each door, sets its state, and keeps English refs for the OWB', () => {
		const doors = resolveDoors(w, entries, shelf('en'), 'en', 101);
		expect(doors.map((d) => [d.n, d.day, d.state])).toEqual([
			[1, 100, 'open'],
			[2, 101, 'today'],
			[3, 102, 'locked']
		]);
		expect(doors[1]).toMatchObject({ title: 'Ch 30', source: 'Waiting', ref: 'Luke 12:36', owbRef: 'Luke 12:36' });
	});

	it('shows only doors whose reading exists in the language — no English fallback', () => {
		const doors = resolveDoors(w, entries, shelf('fr'), 'fr', 101);
		expect(doors.map((d) => d.n)).toEqual([1, 2]);
		expect(doors[0]).toMatchObject({ title: 'Un enfant nous est né', ref: 'Ésaïe 9:5', owbRef: '' });
		// A chapter's reference is written in English: none is shown in French.
		expect(doors[1]).toMatchObject({ ref: '', owbRef: '' });
	});

	it('a missing chapter drops its door', () => {
		const doors = resolveDoors(w, entries, shelf('en'), 'en', 101);
		expect(doors.find((d) => d.n === 4)).toBeUndefined();
	});

	it('hides a calendar left with too few doors', () => {
		const long = { ...w, days: Array.from({ length: 24 }, (_, i) => 100 + i) };
		const mk = (n: number) => resolveDoors(long, entries.slice(0, 1), shelf('en'), 'en', 100).slice(0, n);
		expect(enoughDoors(long, mk(1))).toBe(false);
		expect(enoughDoors(long, [])).toBe(false);
		const many = Array.from({ length: 8 }, () => mk(1)[0]);
		expect(enoughDoors(long, many)).toBe(true);
		expect(enoughDoors(long, many.slice(0, 7))).toBe(false);
	});
});
