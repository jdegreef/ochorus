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
	{ label: 'series', file: 'routes/series/+page.svelte' },
	// /young-readers/ and /teens/ are one component, like BooksShelf above.
	{ label: 'audience hubs', file: 'lib/components/AudienceHub.svelte' },
	{ label: 'plans', file: 'routes/plans/+page.svelte' },
	{ label: 'sermons', file: 'routes/sermons/+page.svelte' },
	{ label: 'biographies', file: 'routes/biographies/+page.svelte' },
	{ label: 'authors a-z', file: 'routes/authors/+page.svelte' },
	{ label: 'search', file: 'routes/search/+page.svelte' },
	{ label: 'quotes', file: 'routes/quotes/+page.svelte' },
	{ label: 'scripture index', file: 'routes/scripture/+page.svelte' },
	{ label: 'articles', file: 'routes/articles/+page.svelte' },
	// The /articles/<topic>/ shelf shares the [slug] route with the article
	// reader; its content lives in a component, like BooksShelf above.
	{ label: 'articles topic', file: 'lib/components/ArticleTopicShelf.svelte' }
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
	// Both hub routes are thin wrappers; the shell lives in the component.
	{ label: 'hub', file: 'lib/components/HubPage.svelte' },
	{ label: 'topic', file: 'routes/topics/[slug]/+page.svelte' },
	{ label: 'plan', file: 'routes/plans/[slug]/+page.svelte' },
	{ label: 'series', file: 'routes/series/[slug]/+page.svelte' },
	{ label: 'quotes author', file: 'routes/quotes/[author]/+page.svelte' },
	// The [slug] route is a thin switch (article reader vs topic shelf); the
	// reader's shell lives in its component, so the invariant is checked there.
	{ label: 'article', file: 'lib/components/ArticleDetail.svelte' },
	{ label: 'scripture book', file: 'routes/scripture/[book]/+page.svelte' },
	{ label: 'scripture chapter', file: 'routes/scripture/[book]/[chapter]/+page.svelte' },
	{ label: 'scripture verse', file: 'routes/scripture/[book]/[chapter]/[verse]/+page.svelte' },
	{ label: 'error', file: 'routes/+error.svelte' }
];

/**
 * The app-like utility pages (page-design: "Settings and Notebook are app
 * pages"). Not shelves, so the browse padding/type checks don't apply, but
 * their title still goes through <PageHeader> — Settings hand-rolled a copy of
 * it until page-design A9, which is how its tagline lost the shared measure.
 */
const APP_PAGES: { label: string; file: string }[] = [
	{ label: 'notebook', file: 'routes/notebook/+page.svelte' },
	{ label: 'settings', file: 'routes/settings/+page.svelte' },
	{ label: 'welcome', file: 'routes/welcome/+page.svelte' }
];

/**
 * Single-form pages held to a card width. Their shell is `.page-col
 * .page-col--narrow`, not a hand-set `mx-auto max-w-[26rem]` (page-design A11).
 * Login's pitch variant (/login?redirect=/notebook) is a deliberate two-column
 * layout at max-w-5xl, so the class is required somewhere in the file rather
 * than as the only shell.
 */
const NARROW_PAGES: { label: string; file: string }[] = [
	{ label: 'login', file: 'routes/login/+page.svelte' },
	{ label: 'reset password', file: 'routes/reset-password/+page.svelte' }
];

const SHELL_PAGES = [...BROWSE_PAGES, ...LEAF_PAGES, ...APP_PAGES];

const read = (file: string) => readFileSync(join(SRC, file), 'utf8');

describe('pages use the shared page furniture', () => {
	it.each(SHELL_PAGES)('$label wraps its content in .page-col', ({ file }) => {
		expect(
			read(file),
			`${file}: every page's outermost container must be .page-col, so one ` +
				`Page width preference moves all of them together (STYLE_GUIDE §3).`
		).toMatch(/class="page-col/);
	});

	it.each([...BROWSE_PAGES, ...APP_PAGES])('$label renders its title through <PageHeader>', ({ file }) => {
		expect(
			read(file),
			`${file}: use <PageHeader> rather than a hand-rolled <h1> block, or the ` +
				`eyebrow/title/tagline spacing drifts per page (STYLE_GUIDE §5).`
		).toMatch(/<PageHeader\b/);
	});

	it.each(BROWSE_PAGES)('$label uses the standard shell padding', ({ file }) => {
		// The vertical axis is what drifted — shells sat at py-6 / py-8 / py-10, so
		// the content edge jumped on every navigation. py-10 is the one value.
		// (Home-section components legitimately use pt-14 and are not browse pages;
		// the leaf +error keeps its own centred layout, so this is BROWSE-only.)
		expect(
			read(file),
			`${file}: browse shells are "page-col px-5 py-10" (STYLE_GUIDE §3).`
		).toMatch(/class="page-col px-5 py-10\b/);
	});

	it.each(NARROW_PAGES)('$label sits on .page-col--narrow, not a hand-set width', ({ file }) => {
		const src = read(file);
		expect(
			src,
			`${file}: a single-form page's shell is "page-col page-col--narrow" (app.css), ` +
				`so its width lives in one place.`
		).toMatch(/class="[^"]*\bpage-col page-col--narrow\b/);
		expect(
			src.match(/\bmax-w-\[[^\]]+\]/g) ?? [],
			`${file}: a hand-set max-w-[…] is the shell .page-col--narrow replaced.`
		).toEqual([]);
	});

	it.each(SHELL_PAGES)('$label does not re-introduce its own max-w shell', ({ file }) => {
		// `mx-auto max-w-*` on a page's own container is what .page-col replaced.
		// Inner elements may still cap a text measure — this only catches the
		// centred page-shell form. Arbitrary widths (`max-w-[26rem]`) and `xl`
		// count too: Login and Reset hid a shell that way until page-design A11.
		expect(
			read(file).match(
				/class="[^"]*\bmx-auto max-w-(?:xl|2xl|3xl|4xl|5xl|6xl|7xl|\[[^\]]+\])(?![\w-])/g
			) ?? [],
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

/**
 * The shelf controls are shared components, not per-page copies (the
 * 2026-10-03 shelf-consistency pass). Each of these was written out by hand on
 * two to five shelves and had drifted: a different sticky recipe per page, two
 * A–Z rails with different padding, grid/list in opposite orders.
 */
describe('shelf controls come from the shared components', () => {
	/** The long shelves whose controls pin under the app nav. */
	const PINNED = ['books', 'sermons', 'biographies', 'authors a-z'];
	it.each(BROWSE_PAGES.filter((p) => PINNED.includes(p.label)))(
		'$label pins its controls with <FilterBar>',
		({ file }) => {
			const src = read(file);
			expect(src, `${file}: wrap the shelf's controls in <FilterBar>.`).toContain('<FilterBar');
			expect(
				src.match(/class="[^"]*\bsticky\b[^"]*border-b/g) ?? [],
				`${file}: a hand-rolled sticky controls bar — use <FilterBar> (it owns ` +
					`the offset, the rule and the measured height).`
			).toEqual([]);
		}
	);

	it.each(BROWSE_PAGES)('$label draws grid/list with <ViewToggle>, if at all', ({ file }) => {
		const src = read(file);
		expect(
			/<Icon name="(grid|list)"/.test(src),
			`${file}: the grid/list switch is <ViewToggle> (grid first, same icons everywhere).`
		).toBe(false);
	});

	it.each(BROWSE_PAGES)('$label jumps by letter with <AzRail>, if at all', ({ file }) => {
		const src = read(file);
		expect(
			/aria-label=\{t\('bios\.jumpAz'\)\}/.test(src) && !src.includes('<AzRail'),
			`${file}: an A–Z jump is <AzRail> (anchors or reveal-then-scroll buttons).`
		).toBe(false);
	});
});
