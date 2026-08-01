import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * The browse pages must keep using the shared page furniture.
 *
 * Everything this guards was hand-written per page at some point, and drifted:
 * six pages ended up at five different widths, two different page-title sizes,
 * four different filter-row layouts, and the same input styled two ways. The
 * fixes landed in #718, #720 and #722; the STYLE_GUIDE now documents them. But
 * a guide is a convention, and conventions lose to the next person in a hurry
 * — so the invariants are asserted here.
 *
 * This is deliberately a SHAPE check, not a design check. It says "use the
 * shared shell and header", never "look like this", so a page can be redesigned
 * freely as long as it keeps standing on the system.
 */

const SRC = join(import.meta.dirname, '..');

/** Browse surfaces. Home is excluded: it's a marketing hero, not a shelf. */
const BROWSE_PAGES: { label: string; file: string }[] = [
	{ label: 'books', file: 'lib/components/BooksShelf.svelte' },
	{ label: 'topics', file: 'routes/topics/+page.svelte' },
	{ label: 'plans', file: 'routes/plans/+page.svelte' },
	{ label: 'sermons', file: 'routes/sermons/+page.svelte' },
	{ label: 'biographies', file: 'routes/biographies/+page.svelte' },
	{ label: 'search', file: 'routes/search/+page.svelte' }
];

const read = (file: string) => readFileSync(join(SRC, file), 'utf8');

describe('browse pages use the shared page furniture', () => {
	it.each(BROWSE_PAGES)('$label wraps its content in .page-col', ({ file }) => {
		expect(
			read(file),
			`${file}: every browse page's outermost container must be .page-col, so one ` +
				`Page width preference moves all of them together (STYLE_GUIDE §3).`
		).toMatch(/class="page-col/);
	});

	it.each(BROWSE_PAGES)('$label renders its title through <PageHeader>', ({ file }) => {
		expect(
			read(file),
			`${file}: use <PageHeader> rather than a hand-rolled <h1> block, or the ` +
				`eyebrow/title/tagline spacing drifts per page (STYLE_GUIDE §5).`
		).toMatch(/<PageHeader\b/);
	});

	it.each(BROWSE_PAGES)('$label does not re-introduce its own max-w shell', ({ file }) => {
		// `mx-auto max-w-*` on a page's own container is what .page-col replaced.
		// Inner elements may still cap a text measure — this only catches the
		// centred page-shell form.
		expect(
			read(file).match(/class="[^"]*\bmx-auto max-w-(?:3xl|4xl|5xl|6xl|7xl)\b/g) ?? [],
			`${file}: page shells come from .page-col now. A per-page max-w-* is how ` +
				`the six browse pages ended up at five different widths.`
		).toEqual([]);
	});
});

describe('the type scale is used, not bypassed', () => {
	it.each(BROWSE_PAGES)('$label uses no arbitrary text sizes', ({ file }) => {
		expect(
			read(file).match(/text-\[[^\]]+\]/g) ?? [],
			`${file}: pick the nearest --fs-* step (text-eyebrow / text-small / ` +
				`text-body / text-h1..h3) instead of an arbitrary value (STYLE_GUIDE §2).`
		).toEqual([]);
	});

	it('.text-display is reserved for the home hero', () => {
		const offenders = BROWSE_PAGES.filter(({ file }) => read(file).includes('text-display'));
		expect(
			offenders.map((o) => o.label),
			'.text-display is the hero size. Browse-page titles are .text-h1, which ' +
				'<PageHeader> already applies (STYLE_GUIDE §2).'
		).toEqual([]);
	});
});
