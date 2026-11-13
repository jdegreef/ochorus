import { describe, it, expect } from 'vitest';
import {
	PRIMARY_NAV,
	SECTION_DESTS,
	SERIES_DEST,
	ENGLISH_HUBS,
	TABLET_MORE_SECTIONS,
	primaryNav,
	hubDests
} from './contentNav';
import { BIBLE_PATH, BIBLE_LOCALES } from './bible';

/**
 * The nav, the footer Explore group and the command palette all `.map` these
 * two arrays, so this pins the ONE order they share. If a destination is added,
 * removed or reordered, that is a real chrome change and this test should be
 * updated deliberately — the point of F2 is that the order lives in exactly one
 * place, and this guards that it is the intended one.
 */
describe('contentNav', () => {
	it('keeps the primary nav order Books · Topics · Plans · Sermons · Biographies', () => {
		expect(PRIMARY_NAV.map((d) => d.href)).toEqual([
			'/books',
			'/topics',
			'/plans',
			'/sermons',
			'/biographies'
		]);
	});

	it('puts the Bible between Books and Topics, only where its books have shipped', () => {
		expect(primaryNav('en').map((d) => d.href)).toEqual([
			'/books',
			BIBLE_PATH,
			'/topics',
			'/plans',
			'/sermons',
			'/biographies'
		]);
		expect(primaryNav('en')).toEqual(SECTION_DESTS);
		for (const l of ['es', 'fr', 'sw', 'lg', 'ar'].filter((l) => !BIBLE_LOCALES.includes(l)))
			expect(primaryNav(l), l).toEqual(PRIMARY_NAV);
	});

	it('lists the Bible once: a section, never also a hub', () => {
		for (const l of ['en', 'es']) {
			const hrefs = [...primaryNav(l), ...hubDests(l)].map((d) => d.href);
			expect(new Set(hrefs).size, l).toBe(hrefs.length);
		}
	});

	it('folds only real sections into the tablet More menu', () => {
		const sections = SECTION_DESTS.map((d) => d.section);
		for (const s of TABLET_MORE_SECTIONS) expect(sections).toContain(s);
	});

	it('keeps the English-hub order Articles · Scripture · Quotes', () => {
		expect(ENGLISH_HUBS.map((d) => d.href)).toEqual(['/articles', '/scripture', '/quotes', '/glossary']);
	});

	it('gives every primary destination a label key and an icon', () => {
		for (const d of SECTION_DESTS) {
			expect(d.labelKey).toMatch(/^[a-z]+\.[a-zA-Z]+$/);
			expect(d.icon).toBeTruthy();
		}
	});

	it('gives every hub a label key (no icon — hubs never sit in the top nav)', () => {
		for (const d of ENGLISH_HUBS) {
			expect(d.labelKey).toMatch(/^[a-z]+\.[a-zA-Z]+$/);
		}
	});

	it('uses canonical, trailing-slash-free hrefs (each surface adds its own)', () => {
		for (const d of [...SECTION_DESTS, SERIES_DEST, ...ENGLISH_HUBS]) {
			expect(d.href.startsWith('/')).toBe(true);
			expect(d.href.endsWith('/')).toBe(false);
		}
	});
});
