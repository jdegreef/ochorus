import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { FOR_LINKS, FOR_LOCALES } from './forLinks';
import { forPage, type ForPage } from './forPages';
import { FOR_PLACES, FOR_PROMOS, PROMO_LEAD, PROMO_WORDS, SEARCH_FOR, TOPIC_FOR, promoLocale, searchFor } from './forPromos';
import type { ForSection } from './forSections';

const SLUGS = new Set(FOR_LINKS.map((l) => l.slug));
const TOPIC_SEED = readFileSync(join(import.meta.dirname, '..', '..', '..', 'backend', 'library', 'topic_seed.py'), 'utf8');

/** Is the section a link lands on configured on the English page? */
const configured = (p: ForPage, s: ForSection): boolean =>
	({
		plans: p.plans.length > 0,
		series: !!p.series?.length,
		levels: !!p.levels?.length,
		guides: !!p.guides,
		offline: !!p.offline,
		languages: !!p.languages,
		shelves: p.shelves.length > 0
	})[s as string] ?? true;

describe('links to the "Ochorus for …" pages from the rest of the site', () => {
	it('names only pages that exist, landing on a section the page has', () => {
		for (const [place, promo] of Object.entries(FOR_PROMOS)) {
			expect(promo.slugs.length, place).toBeGreaterThan(0);
			for (const slug of promo.slugs) {
				expect(SLUGS.has(slug), `${place} → ${slug}`).toBe(true);
				if (promo.section) expect(configured(forPage(slug)!, promo.section), `${place} → ${slug}#${promo.section}`).toBe(true);
			}
		}
	});

	it('maps real topics and search words to real pages', () => {
		for (const [topic, slug] of Object.entries(TOPIC_FOR)) {
			expect(TOPIC_SEED.includes(`"${topic}"`), `topic ${topic}`).toBe(true);
			expect(SLUGS.has(slug), `topic ${topic} → ${slug}`).toBe(true);
		}
		for (const slug of Object.values(SEARCH_FOR)) expect(SLUGS.has(slug), slug).toBe(true);
	});

	it('asks each place’s question in every page language', () => {
		for (const locale of FOR_LOCALES) {
			for (const place of FOR_PLACES) expect(PROMO_LEAD[locale][place], `${locale} ${place}`).toBeTruthy();
			expect(PROMO_WORDS[locale].all).toBeTruthy();
		}
	});

	it('finds the group a search names, preferring the longer phrase, and ignores the rest', () => {
		expect(searchFor('Homeschool')).toBe('homeschool');
		expect(searchFor('books for a small group')).toBe('small-groups');
		expect(searchFor('Bible college reading')).toBe('bible-colleges');
		expect(searchFor('prayer')).toBeNull();
		expect(searchFor('churchill')).toBeNull();
	});

	it('shows only where the pages are written', () => {
		expect(promoLocale('fr')).toBe('fr');
		expect(promoLocale('sw')).toBeNull();
	});
});
