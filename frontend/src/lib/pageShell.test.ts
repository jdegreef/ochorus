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

/**
 * The leaf pages you reach FROM a browse surface. They share the page column
 * but not <PageHeader>: each has its own header shape (a cover beside a title,
 * a portrait and a timeline, an emblem in a tinted hero), so only the shell is
 * asserted here.
 *
 * Converting the browse pages alone left the stepper half-working — it moved
 * Books and then did nothing on the book opened from it. Excluded on purpose:
 * the chapter reader and the sermon page answer to `--reading-measure`, and
 * About / Contact / Legal are prose at their own measure.
 */
const LEAF_PAGES: { label: string; file: string }[] = [
	{ label: 'book', file: 'routes/books/[slug]/+page.svelte' },
	{ label: 'author', file: 'routes/authors/[slug]/+page.svelte' },
	{ label: 'era', file: 'routes/biographies/era/[era]/+page.svelte' },
	{ label: 'topic', file: 'routes/topics/[slug]/+page.svelte' },
	{ label: 'plan', file: 'routes/plans/[slug]/+page.svelte' },
	{ label: 'quotes', file: 'routes/quotes/[author]/+page.svelte' },
	{ label: 'scripture index', file: 'routes/scripture/+page.svelte' },
	{ label: 'scripture chapter', file: 'routes/scripture/[book]/[chapter]/+page.svelte' },
	{ label: 'scripture verse', file: 'routes/scripture/[book]/[chapter]/[verse]/+page.svelte' },
	{ label: 'notebook', file: 'routes/notebook/+page.svelte' },
	{ label: 'settings', file: 'routes/settings/+page.svelte' },
	{ label: 'error', file: 'routes/+error.svelte' }
];

const SHELL_PAGES = [...BROWSE_PAGES, ...LEAF_PAGES];

const read = (file: string) => readFileSync(join(SRC, file), 'utf8');

describe('pages use the shared page furniture', () => {
	it.each(SHELL_PAGES)('$label wraps its content in .page-col', ({ file }) => {
		expect(
			read(file),
			`${file}: every page's outermost container must be .page-col, so one ` +
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

	it.each(SHELL_PAGES)('$label does not re-introduce its own max-w shell', ({ file }) => {
		// `mx-auto max-w-*` on a page's own container is what .page-col replaced.
		// Inner elements may still cap a text measure — this only catches the
		// centred page-shell form.
		expect(
			read(file).match(/class="[^"]*\bmx-auto max-w-(?:2xl|3xl|4xl|5xl|6xl|7xl)\b/g) ?? [],
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
