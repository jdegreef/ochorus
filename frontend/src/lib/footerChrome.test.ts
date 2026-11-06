import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const read = (f: string) => readFileSync(join(process.cwd(), f), 'utf-8');
const FOOTER = read('src/lib/components/SiteFooter.svelte');
const FAB = read('src/lib/components/FeedbackFab.svelte');

describe('the floating feedback button and the footer', () => {
	it('steps aside once the footer’s "Send feedback" row is reached', () => {
		expect(FOOTER).toMatch(/footerFeedback\.reached\s*=/);
		expect(FOOTER).toMatch(/<nav class="footer-legal[^"]*"[^>]*bind:this=\{feedbackRow\}/);
		expect(FAB).toMatch(/!footerFeedback\.reached \|\| focused/);
	});

	it('the watched row keeps the "Send feedback" entry', () => {
		const legal = FOOTER.slice(FOOTER.indexOf('<nav class="footer-legal'));
		expect(legal.slice(0, legal.indexOf('</nav>'))).toContain("t('feedback.send')");
	});
});

/*
 * Design #3, "A one-band footer": the footer had grown five bands (~930px on
 * every page). These pin the one band, so a future addition is a decision, not
 * a drift back.
 */
describe('one band', () => {
	it('has exactly two link columns, Read and More, both through linkColumn', () => {
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

describe('language select', () => {
	const GENERATOR = read('scripts/fetch-live-locales.mjs');

	it('bakes each live language\'s book count from the API at build time', () => {
		expect(GENERATOR).toMatch(/row\?\.book_count/);
		expect(GENERATOR).toContain('export const LIVE_LOCALE_BOOKS');
	});

	it('words the count beside the autonym, and nothing for a language with none', () => {
		expect(FOOTER).toContain("import { LIVE_LOCALE_BOOKS } from '$lib/live-locales.generated'");
		expect(FOOTER).toMatch(/if \(!n\) return name;/);
	});

	it('switches through lang.choose(), voicing each option in its own language', () => {
		expect(FOOTER).toMatch(/onchange=\{\(e\) => lang\.choose\(e\.currentTarget\.value\)\}/);
		expect(FOOTER).toMatch(/<option value=\{l\.code\} lang=\{l\.code\}/);
	});
});
