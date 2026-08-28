import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { READER_ROUTE_IDS, isReaderRoute } from './readerRoutes';

const SRC = join(import.meta.dirname, '..');
const read = (file: string) => readFileSync(join(SRC, file), 'utf8');

describe('isReaderRoute', () => {
	it.each(READER_ROUTE_IDS)('recognises %s', (id) => {
		expect(isReaderRoute(id)).toBe(true);
	});

	it.each([
		'/books/[slug]',
		'/sermons',
		'/authors/[slug]',
		'/quotes/[author]',
		'/settings',
		'/'
	])('leaves %s alone', (id) => {
		expect(isReaderRoute(id)).toBe(false);
	});

	it('tolerates a null route id', () => {
		// `$page.route.id` is null before the first navigation resolves, and a
		// throw there would take the whole nav down.
		expect(isReaderRoute(null)).toBe(false);
		expect(isReaderRoute(undefined)).toBe(false);
	});
});

describe('the reading surfaces are named in one place', () => {
	// The route ids used to be spelled out inline in the layout. A second reader
	// behaviour (hiding the dead Page width stepper) needed the same list, and a
	// route id living in two files is a route id that gets updated in one.
	it.each(['routes/+layout.svelte', 'lib/components/QuickSettings.svelte'])(
		'%s asks the helper rather than matching route ids itself',
		(file) => {
			const src = read(file);
			expect(src, `${file}: import isReaderRoute from $lib/readerRoutes.`).toMatch(
				/isReaderRoute/
			);
			expect(
				src.match(/'\/(?:books\/\[slug\]\/\[order\]|sermons\/\[slug\])'/g) ?? [],
				`${file}: don't re-spell a reading-surface route id — READER_ROUTE_IDS is the list.`
			).toEqual([]);
		}
	);
});

describe('the Page width stepper hides on the reading surfaces', () => {
	// A chapter and a sermon size their column from --reading-measure, owned by
	// their own `A a` popover. The stepper rendered there anyway: it opened, it
	// stored a new value, and the article never moved.
	const src = read('lib/components/QuickSettings.svelte');

	it('gates the width row on the route', () => {
		expect(src, 'QuickSettings: wrap the Page width row in {#if !inReader}.').toMatch(
			/\{#if !inReader\}/
		);
	});

	it('gates the width row and nothing else', () => {
		// The theme toggle applies everywhere, including in the reader — if it
		// drifted inside the guard, dark mode would vanish from the two pages
		// people spend the most time on.
		const guarded = src.slice(src.indexOf('{#if !inReader}'));
		const row = guarded.slice(0, guarded.indexOf('{/if}'));
		expect(row).toMatch(/nav\.pageWidth/);
		expect(row, 'the theme toggle must stay outside the reader guard').not.toMatch(/nav\.theme/);
	});

	it('still adopts the stored width in the reader', () => {
		// pageWidth.init() must stay outside the guard: the preference has to be
		// live when the reader navigates BACK to a browse page, and init() runs
		// once per mount of this always-mounted component.
		expect(src, 'pageWidth.init() belongs in onMount, not inside the width row.').toMatch(
			/onMount\(\(\) => pageWidth\.init\(\)\)/
		);
	});
});
