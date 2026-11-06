import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * Two rules the search surfaces broke in ways only a screenshot revealed.
 *
 * Source-text checks, in the idiom `colorTokens.test.ts` and `rtl.test.ts` use:
 * jsdom applies no stylesheet and lays out nothing, so neither of these can be
 * asserted by rendering. What can be asserted is that the specific construct
 * that failed has not come back.
 */
const read = (p: string) => readFileSync(join(process.cwd(), p), 'utf-8');

// The type facet was a left rail above lg until design review #25 (2026-11-06)
// moved it into tabs under the field. The rail's own guards — a minmax track so
// the sort control could not overhang the results, and a stacked sort label —
// went with the rail; these keep what replaced it from regressing.
describe('the search page facet is a row of tabs under the field', () => {
	const source = read('src/routes/search/+page.svelte');

	it('draws the kinds as one sideways-scrolling tab row, not a wrapping chip wall or a rail', () => {
		// A phone holds three or four tabs; the strip scrolls rather than wrapping
		// onto a second line under the pinned field, which would eat the screen.
		expect(source).toMatch(/class="tab-strip flex gap-1" use:tabStrip/);
		expect(source).not.toMatch(/lg:grid-cols-\[minmax\(12rem/);
		expect(source).not.toMatch(/lg:sticky[^"]*lg:flex-col/);
	});

	it('pins the tabs with the field, so switching kind never means scrolling up', () => {
		const sticky = source.indexOf('bind:clientHeight={searchBarH}');
		const tabs = source.indexOf("aria-label={t('search.filterByType')}");
		const results = source.indexOf('id="search-results"');
		expect(sticky).toBeGreaterThan(-1);
		expect(tabs).toBeGreaterThan(sticky);
		expect(tabs).toBeLessThan(results);
	});

	it('renders snippets as text runs, never {@html}', () => {
		// Snippets are untrusted text with the server's match markers in them.
		expect(source).not.toMatch(/\{@html/);
	});
});

describe('the command palette leads with the way out', () => {
	const source = read('src/lib/components/CommandPalette.svelte');

	it('puts the full-search row first, before the commands and hits', () => {
		// Last, it sat under however many instant hits the query drew — so the one
		// row that reaches the whole library was the one you had to scroll for.
		// First, it is also what Enter runs by default.
		const items = source.split('\n').find((line) => line.includes('const items = $derived'));
		expect(items).toBeTruthy();
		const order = ['searchItem', 'cmdItems', 'hitItems'].map((name) => items!.indexOf(name));
		expect(order.every((i) => i >= 0)).toBe(true);
		expect(order).toEqual([...order].sort((a, b) => a - b));
	});
});
