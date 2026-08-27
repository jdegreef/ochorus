import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';

/**
 * The advertised-locales gate, pinned at the source.
 *
 * Books, sermons and plans are per-language rows with no English fallback, and
 * `advertised-locales.ts` exists so a locale with an empty catalog is never
 * offered to a crawler. `sitemap.xml`, the detail pages and the footer all
 * honour it — but the six INDEX pages built their alternates from Paraglide's
 * full `locales` list instead, so the site made two contradictory hreflang
 * claims and the wrong one was on its most-crawled pages. Nothing caught it,
 * because a wrong hreflang is invisible in a code review of an unrelated change
 * and invisible in the browser.
 *
 * So: no route may render an hreflang alternate from the raw locale list. Use
 * `hreflangAll` (every advertised locale) or `hreflangFor` (the locales a work
 * actually exists in), both in `seo.ts`.
 */
const ROUTES = resolve(__dirname, '../routes');

function svelteFiles(dir: string): string[] {
	const out: string[] = [];
	for (const entry of readdirSync(dir, { withFileTypes: true })) {
		const full = join(dir, entry.name);
		if (entry.isDirectory()) out.push(...svelteFiles(full));
		else if (entry.name.endsWith('.svelte')) out.push(full);
	}
	return out;
}

describe('hreflang is gated on the advertised locales', () => {
	it('no route builds alternates from the full locale list', () => {
		const offenders: string[] = [];
		for (const file of svelteFiles(ROUTES)) {
			const src = readFileSync(file, 'utf8');
			if (!src.includes('rel="alternate"')) continue;
			// Either shape of the bug: iterating `locales` in the markup, or
			// mapping it into an `alternates` array in the script.
			const iterates = /\{#each\s+locales\s+as\b/.test(src);
			const maps = /\blocales\s*\.\s*map\s*\(/.test(src);
			if (iterates || maps) offenders.push(file.slice(ROUTES.length + 1));
		}
		expect(offenders).toEqual([]);
	});

	it('sitemap and the gate agree on what is advertised', async () => {
		// Guards the direction of the fix: hreflangAll must be built from
		// ADVERTISED_LOCALES, not from every configured UI locale.
		const { ADVERTISED_LOCALES } = await import('./advertised-locales');
		const { locales } = await import('$lib/paraglide/runtime');
		const { hreflangAll } = await import('./seo');
		const advertised = hreflangAll('/books').alternates.map((a) => a.loc);
		expect(advertised).toEqual([...ADVERTISED_LOCALES]);
		// And the two lists genuinely differ today — otherwise this whole gate
		// would be passing for the wrong reason.
		expect(locales.length).toBeGreaterThan(ADVERTISED_LOCALES.length);
	});
});
