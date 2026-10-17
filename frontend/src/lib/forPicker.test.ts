import { describe, expect, it } from 'vitest';
import { FOR_CHROME } from './forChrome';
import { FOR_LINKS, FOR_LOCALES, forPath } from './forLinks';
import { forPage, type ForPage } from './forPages';
import { FOR_GOALS, GOAL_SECTION, PICKER_GOALS, pickerHref, type ForGoal } from './forPicker';

/** Is the section a goal lands on configured on this page? */
const configured: Record<ForGoal, (p: ForPage) => boolean> = {
	together: (p) => p.plans.length > 0,
	series: (p) => !!p.series?.length,
	young: (p) => !!p.levels?.length,
	guides: (p) => !!p.guides,
	offline: (p) => !!p.offline,
	languages: (p) => !!p.languages,
	books: (p) => p.shelves.length > 0
};

describe('the /for/ picker', () => {
	it('asks about every group, in every page language', () => {
		expect(Object.keys(PICKER_GOALS).sort()).toEqual(FOR_LINKS.map((l) => l.slug).sort());
		for (const locale of FOR_LOCALES) {
			const { roles, goals } = FOR_CHROME[locale].picker;
			for (const l of FOR_LINKS) expect(roles[l.slug], `${locale} role ${l.slug}`).toBeTruthy();
			for (const g of FOR_GOALS) expect(goals[g], `${locale} goal ${g}`).toBeTruthy();
		}
	});

	it('offers exactly the goals each page has a section for', () => {
		for (const locale of FOR_LOCALES)
			for (const l of FOR_LINKS) {
				const page = forPage(l.slug, locale)!;
				const offered = PICKER_GOALS[l.slug][locale];
				expect(new Set(offered).size, `${locale}/${l.slug} repeats a goal`).toBe(offered.length);
				expect([...offered].sort(), `${locale}/${l.slug}`).toEqual(FOR_GOALS.filter((g) => configured[g](page)).sort());
			}
	});

	it('lands on the goal’s section of the group’s page', () => {
		expect(pickerHref(forPath('chaplains', 'fr'), 'offline')).toBe('/fr/for/chaplains/#offline');
		expect(GOAL_SECTION.together).toBe('plans');
	});
});
