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

describe('the search page rail cannot overhang the results', () => {
	const source = read('src/routes/search/+page.svelte');

	it('sizes its column to fit its contents, not to a flat width', () => {
		// A fixed track does not clip an over-wide child, it lets it hang out over
		// the next column: with a type chosen, the chips and the sort control (a
		// 244px min-content) painted across the first result's heading and cover.
		expect(source).toMatch(/lg:grid-cols-\[minmax\(12rem,\s*auto\)_1fr\]/);
		expect(source).not.toMatch(/lg:grid-cols-\[12rem_1fr\]/);
	});

	it('stacks the sort label above its buttons once it is in the rail', () => {
		// "Sort:" BESIDE a three-button segment is what made the control wider than
		// the column in the first place. Beside it stays in the wide bar below lg.
		const sortGroup = source
			.split('\n')
			.find((line) => line.includes("aria-label={t('search.sortBy')}"));
		expect(sortGroup).toBeTruthy();
		const block = source.slice(0, source.indexOf("aria-label={t('search.sortBy')}"));
		const opening = block.slice(block.lastIndexOf('<div'));
		expect(opening).toContain('lg:flex-col');
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
