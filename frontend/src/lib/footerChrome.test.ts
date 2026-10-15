import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const read = (f: string) => readFileSync(join(process.cwd(), f), 'utf-8');
const FOOTER = read('src/lib/components/SiteFooter.svelte');
const FAB = read('src/lib/components/FeedbackFab.svelte');

describe('the floating feedback button and the footer', () => {
	it('steps aside once the footer’s Account column (its "Send feedback") is reached', () => {
		expect(FOOTER).toMatch(/footerFeedback\.reached\s*=/);
		expect(FOOTER).toContain("getElementById('footer-account-heading')");
		expect(FAB).toMatch(/!footerFeedback\.reached \|\| focused/);
	});

	it('the Account column keeps the "Send feedback" entry it is watched for', () => {
		const account = FOOTER.slice(FOOTER.indexOf('{#snippet accountList()}'));
		expect(account.slice(0, account.indexOf('{/snippet}'))).toContain("t('feedback.send')");
	});
});

describe('phone link columns', () => {
	it('fold in CSS, so the prerendered page carries every link and nothing reflows', () => {
		expect(FOOTER).toMatch(/\.footer-col:not\(\.open\) :global\(\.footer-links\)\s*\{\s*display: none;/);
		expect(FOOTER).not.toMatch(/mediaFlag\(/);
	});

	it('every link column goes through linkColumn', () => {
		expect(FOOTER.match(/\{@render linkColumn\(/g)?.length).toBe(3);
		expect(FOOTER).not.toMatch(/<nav aria-labelledby="footer-/);
	});
});

describe('language tiles', () => {
	const GENERATOR = read('scripts/fetch-live-locales.mjs');

	it('bake each live language\'s book count from the API at build time', () => {
		expect(GENERATOR).toMatch(/row\?\.book_count/);
		expect(GENERATOR).toContain('export const LIVE_LOCALE_BOOKS');
	});

	it('print the count under the autonym, and nothing for a language with none', () => {
		expect(FOOTER).toContain("import { LIVE_LOCALE_BOOKS } from '$lib/live-locales.generated'");
		expect(FOOTER).toMatch(/\{#if LIVE_LOCALE_BOOKS\[code\]\}/);
		expect(FOOTER.match(/\{@render tile\(/g)?.length).toBe(2);
	});
});
