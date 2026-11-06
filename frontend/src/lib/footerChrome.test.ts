import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const read = (f: string) => readFileSync(join(process.cwd(), f), 'utf-8');
const FOOTER = read('src/lib/components/SiteFooter.svelte');
const FAB = read('src/lib/components/FeedbackFab.svelte');

describe('the floating feedback button and the footer', () => {
	it('steps aside once the band carrying "Send feedback" is reached', () => {
		expect(FOOTER).toMatch(/footerFeedback\.reached\s*=/);
		expect(FOOTER).toMatch(/<div class="footer-band[^"]*"[^>]*bind:this=\{band\}/);
		expect(FAB).toMatch(/!footerFeedback\.reached \|\| focused/);
	});

	it('the band keeps the "Send feedback" entry', () => {
		const band = FOOTER.slice(FOOTER.indexOf('<div class="footer-band'));
		expect(band.slice(0, band.indexOf('<!-- Bible credit'))).toContain("t('feedback.send')");
	});
});

/*
 * Design #3, "A one-band footer": the footer had grown five bands (~930px on
 * every page). These pin the one band, so a future addition is a decision, not
 * a drift back.
 */
describe('one band', () => {
	it('has exactly two link columns, Library and More, both through linkColumn', () => {
		expect(FOOTER.match(/\{@render linkColumn\(/g)?.length).toBe(2);
		expect(FOOTER).not.toMatch(/<nav aria-labelledby="footer-/);
	});

	it('links the /for/ hub once instead of every audience page', () => {
		expect(FOOTER).toContain('forIndexPath(forLang)');
		expect(FOOTER).not.toMatch(/forPath\(|FOR_LINKS|forFamilyLinks/);
	});

	it('draws no generic library cards — only a personal next step', () => {
		expect(FOOTER).not.toContain("t('seals.nextBooks')");
		expect(FOOTER).not.toContain("t('seals.nextPlans')");
		expect(FOOTER).toMatch(/pageShowsBook\(path, item\.slug\)/);
	});
});

describe('language switcher', () => {
	const GENERATOR = read('scripts/fetch-live-locales.mjs');

	it('bakes each live language\'s book count from the API at build time', () => {
		expect(GENERATOR).toMatch(/row\?\.book_count/);
		expect(GENERATOR).toContain('export const LIVE_LOCALE_BOOKS');
	});

	it('prints the count beside the autonym, and nothing for a language with none', () => {
		expect(FOOTER).toContain("import { LIVE_LOCALE_BOOKS } from '$lib/live-locales.generated'");
		expect(FOOTER).toMatch(/\{#if LIVE_LOCALE_BOOKS\[l\.code\]\}/);
	});

	// Not a <select>: one that switches on `change` jumps language on the first
	// arrow key, does nothing before hydration, and drops the per-page links to
	// every locale's home. Real links, the click recorded through choose().
	it('lists real links to each locale home, switching through lang.choose()', () => {
		expect(FOOTER).not.toMatch(/<select\s/);
		expect(FOOTER).toMatch(/href=\{localizeHref\('\/', \{ locale: l\.code/);
		expect(FOOTER).toMatch(/isUnmodifiedPrimaryClick\(e\)[\s\S]{0,120}lang\.choose\(l\.code\)/);
	});
});
