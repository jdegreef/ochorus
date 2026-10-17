import { describe, expect, it } from 'vitest';
import { FOR_CHROME } from './forChrome';
import { FOR_LINKS, FOR_LOCALES } from './forLinks';
import { EMPTY_SHELF_DATA, type ForShelfData } from './forPages';
import { FOR_LEAD, FOR_SECTIONS, forSectionOrder, hasSection, navSections } from './forSections';
import { seriesDates, seriesICS } from './forSeries';

/** A snapshot with something in every section. */
const FULL = {
	...EMPTY_SHELF_DATA,
	shelves: [{ title: 'S', note: '', books: [{}] }],
	plans: [{}],
	guides: [{}],
	offline: [{}],
	authors: [{}],
	quote: {},
	series: [{ title: 'T', note: '', sermons: [{}] }],
	levels: [[{}]],
	languages: [{}]
} as unknown as ForShelfData;

describe('the order a page tells its story in', () => {
	it('has a lead for every group, naming each section at most once', () => {
		expect(Object.keys(FOR_LEAD).sort()).toEqual(FOR_LINKS.map((l) => l.slug).sort());
		for (const lead of Object.values(FOR_LEAD)) {
			expect(new Set(lead).size).toBe(lead.length);
			for (const s of lead) expect(FOR_SECTIONS).toContain(s);
		}
	});

	it('leads with the group’s sections, then every other one in the default order', () => {
		const order = forSectionOrder('chaplains', FULL);
		expect(order.slice(0, FOR_LEAD.chaplains.length)).toEqual(FOR_LEAD.chaplains);
		expect([...order].sort()).toEqual([...FOR_SECTIONS].sort());
		const rest = order.slice(FOR_LEAD.chaplains.length);
		expect(rest).toEqual(FOR_SECTIONS.filter((s) => rest.includes(s)));
	});

	it('gives each group a different opening', () => {
		const openings = FOR_LINKS.map((l) => forSectionOrder(l.slug, FULL).slice(0, 2).join());
		expect(new Set(openings).size).toBeGreaterThanOrEqual(FOR_LINKS.length - 2);
	});

	it('drops a section with nothing to draw, but always keeps the copy', () => {
		const order = forSectionOrder('missionaries', EMPTY_SHELF_DATA);
		expect(order).toEqual(['why', 'ideas', 'invite', 'questions']);
		expect(hasSection('quote', EMPTY_SHELF_DATA)).toBe(false);
		expect(hasSection('writers', FULL)).toBe(true);
	});

	it('lists every section but the quotation on the jump bar, each named in every page language', () => {
		const nav = navSections(forSectionOrder('churches', FULL));
		expect(nav).not.toContain('quote');
		expect(nav).toHaveLength(FOR_SECTIONS.length - 1);
		for (const locale of FOR_LOCALES) for (const s of nav) expect(FOR_CHROME[locale].nav[s]).toBeTruthy();
	});

	it('gives the page sections the ids the jump bar and the hero buttons land on', async () => {
		const { readFileSync } = await import('node:fs');
		const { join } = await import('node:path');
		const src = readFileSync(join(import.meta.dirname, '..', 'routes', 'for', '[group]', '+page.svelte'), 'utf8');
		const qa = readFileSync(join(import.meta.dirname, 'components', 'QandA.svelte'), 'utf8');
		for (const s of navSections([...FOR_SECTIONS]))
			expect(src.includes(`id="${s}"`) || qa.includes(`id="${s}"`), `#${s} has no section`).toBe(true);
	});
});

describe('a sermon series on the calendar', () => {
	it('meets on the same weekday each week from the first meeting', () => {
		const dates = seriesDates('2026-10-29', 3);
		expect(dates.map((d) => [d.getFullYear(), d.getMonth() + 1, d.getDate(), d.getDay()])).toEqual([
			[2026, 10, 29, 4],
			[2026, 11, 5, 4],
			[2026, 11, 12, 4]
		]);
		expect(seriesDates('not a date', 3)).toEqual([]);
	});

	it('names each week’s sermon and links to it', () => {
		const sermon = (slug: string, title: string) => ({
			slug,
			title,
			scripture_ref: '',
			author: { slug: 'a', name: 'A' },
			questions: 3,
			word_count: 4000
		});
		const ics = seriesICS(
			{ title: 'Six weeks on prayer', sermons: [sermon('one', 'Do You Pray?'), sermon('two', 'Prevailing Prayer')] },
			'2026-11-02',
			{ now: new Date(Date.UTC(2026, 9, 17)), week: (n) => `Week ${n}`, sermonUrl: (s) => `https://ochorus.com/sermons/${s}/` }
		);
		expect(ics.match(/BEGIN:VEVENT/g)).toHaveLength(2);
		expect(ics).toContain('DTSTART;VALUE=DATE:20261102');
		expect(ics).toContain('DTSTART;VALUE=DATE:20261109');
		expect(ics).toContain('SUMMARY:Week 2 · Prevailing Prayer — Six weeks on prayer');
		expect(ics).toContain('URL:https://ochorus.com/sermons/two/');
		expect(ics).toContain('UID:ochorus-series-six-weeks-on-prayer-2026-11-02-1');
	});
});
