import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { AUTHOR_DAYS, anniversariesOn, anniversaryOn } from './authorDays';
import { isDateKey } from './dailyDate';
import { anniversaryDate, anniversaryYear } from './anniversaryFormat';

const AUTHORS = JSON.parse(
	readFileSync(join(__dirname, '..', '..', '..', 'backend', 'library', 'fixtures', 'content', 'authors.json'), 'utf8')
) as { fields: { slug: string; name: string; birth_year: number | null; death_year: number | null } }[];
const BY_SLUG = new Map(AUTHORS.map((a) => [a.fields.slug, a.fields]));

describe('AUTHOR_DAYS', () => {
	it.each(Object.entries(AUTHOR_DAYS))('%s agrees with authors.json', (slug, days) => {
		const author = BY_SLUG.get(slug);
		expect(author, `${slug} is not in authors.json`).toBeDefined();
		expect(days.name).toBe(author!.name);
		expect(days.born ?? days.died, 'a day to keep').toBeTruthy();
		for (const [kind, year] of [
			['born', author!.birth_year],
			['died', author!.death_year]
		] as const) {
			const iso = days[kind];
			if (!iso) continue;
			expect(iso).toMatch(/^\d{4}-\d{2}-\d{2}$/);
			// A real calendar day (no 31 April), in the fixture's year.
			expect(isDateKey(iso.slice(5)), `${slug} ${kind} ${iso}`).toBe(true);
			expect(Number(iso.slice(0, 4)), `${slug} ${kind} year`).toBe(year);
		}
	});
});

describe('anniversaryOn', () => {
	it("finds the writer's day on the reader's local calendar", () => {
		expect(anniversaryOn('augustine-of-hippo', new Date(2026, 10, 13, 0, 5))).toEqual({
			slug: 'augustine-of-hippo',
			name: 'Augustine of Hippo',
			kind: 'born',
			date: '0354-11-13',
			year: 354
		});
		expect(anniversaryOn('augustine-of-hippo', new Date(2026, 7, 28, 23, 55))?.kind).toBe('died');
		expect(anniversaryOn('augustine-of-hippo', new Date(2026, 10, 12, 23, 55))).toBeNull();
		expect(anniversaryOn('no-such-writer', new Date(2026, 10, 13))).toBeNull();
	});
	it('prefers the birth when both fall on the day', () => {
		expect(anniversaryOn('corrie-ten-boom', new Date(2027, 3, 15))?.kind).toBe('born');
	});
});

describe('anniversariesOn', () => {
	it('lists every writer whose day it is, by name', () => {
		const names = anniversariesOn(new Date(2026, 0, 18)).map((a) => a.name);
		expect(names).toEqual(['Amy Carmichael', 'Andrew Murray']);
	});
});

describe('anniversaryDate', () => {
	it('writes the day as it was, ancient years included', () => {
		expect(anniversaryDate('0354-11-13', 'en')).toBe('November 13, 354');
		expect(anniversaryDate('1903-11-04', 'fr')).toBe('4 novembre 1903');
	});
	it("writes the year in the language's digits", () => {
		expect(anniversaryYear(354, 'en')).toBe('354');
		expect(anniversaryYear(1917, 'en')).toBe('1917');
	});
});
