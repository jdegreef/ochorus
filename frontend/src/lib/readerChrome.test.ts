import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * The reader's own toolbar must not end up underneath the global nav.
 *
 * Two changes that were each fine alone collided. The reader's bar became
 * `position: fixed` in page-turn mode (a `sticky` sibling made Chromium drop
 * the top line of later paged columns); separately, the global nav became
 * `.appnav-static` on reading routes, so it sits in flow at the top. In page
 * mode nothing scrolls, so the static nav never leaves — and a `fixed` bar at
 * `top: 0` spent its life underneath it, z-10 against the nav's z-40. Every
 * control in it (Contents, Text settings, Listen, Focus, chapter nav) was
 * invisible and unclickable, at every viewport width, in what is the DEFAULT
 * layout on wide screens. Verified with elementFromPoint: 8 of 8 covered.
 *
 * Since design #7 the reading surfaces draw no site nav at all (one slim
 * reader bar, no site chrome), so the collision is impossible by construction;
 * --appnav-h is 0 there and the checks below hold the pieces that say so.
 *
 * These are source-shape checks, not rendering checks — they can't see a
 * stacking context. What they CAN do is fail when the two invariants that make
 * the collision impossible get reverted by someone who doesn't know the story.
 */

const SRC = join(import.meta.dirname, '..');
const read = (file: string) => readFileSync(join(SRC, file), 'utf8');

const LAYOUT = 'routes/+layout.svelte';
const READER = 'routes/books/[slug]/[order]/+page.svelte';

describe('the layout publishes the nav height as a fact', () => {
	it('zeroes --appnav-h from whether the nav is drawn, not from the route', () => {
		// It used to be `inReader ? 0 : navH` while the reader still drew a static
		// nav: true only in scroll mode, where that nav rode away — and page mode
		// is the case that doesn't scroll. It is now keyed on `siteChrome`, the
		// same switch that draws (or doesn't draw) the nav.
		// Up to the derived's own closing `\n\t);`, not the first `);` (which is
		// inside `var(--safe-top, 0px);`).
		const decl = read(LAYOUT).match(/const appnavH = \$derived\(([\s\S]*?)\n\t\);/)?.[1] ?? '';
		expect(decl, 'could not find the whole --appnav-h declaration').toMatch(/navH\}px/);
		expect(decl, '--appnav-h must be declared from a value, not omitted').not.toEqual('');
		expect(
			decl,
			'--appnav-h is the nav\'s rendered height, not a policy about who clears ' +
				'it. Zeroing it in the reader is what put the page-turn bar under the nav.'
		).not.toMatch(/inReader/);
	});

	it('reports 0 only when the nav is genuinely not rendered', () => {
		// The reading surfaces and focus mode draw no nav (design #7: one slim
		// reader bar, no site chrome), so 0 — or, in the phone app, the status
		// strip's --safe-top — is the truth there. Before the nav is measured (a
		// prerendered browse page) it is left unset, so app.css's per-breakpoint
		// estimate on .app-root holds — never a stand-in 0.
		const src = read(LAYOUT);
		expect(src).toMatch(
			/!siteChrome \? '--appnav-h: var\(--safe-top, 0px\); ' : navH \? `--appnav-h: \$\{navH\}px; ` : ''/
		);
		expect(src).toMatch(/style="[^"]*\{appnavH\}/);
	});

	it('draws the nav and the footer only where siteChrome holds', () => {
		// The one switch: a route that is a reading surface, or focus mode, has
		// neither, so nothing can be pinned underneath a nav that is still there.
		// An error page under a reader route (a 404 chapter) keeps the chrome: the
		// reader's own bar never mounts there.
		const src = read(LAYOUT);
		expect(src).toMatch(/const siteChrome = \$derived\(!\(inReader && !\$page\.error\) && !readerUi\.focus\)/);
		expect(src).toMatch(/\{#if siteChrome\}\s*<nav/);
		expect(src).toMatch(/\{#if siteChrome\}\s*<SiteFooter \/>/);
	});
});

describe('the reading surfaces keep the site one tap away', () => {
	// With no nav and no footer, the "⋯" group is the way to the rest of Ochorus.
	it.each([READER, 'routes/sermons/[slug]/+page.svelte'])('%s carries ReaderSiteLinks in its "⋯" group', (file) => {
		// The group's LAST child, closing it: `onpick` shuts the "⋯" group, and
		// the group's `</div>` and its `{/if}` follow straight after.
		const src = read(file);
		expect(src, `${file}: no "⋯" group found.`).toMatch(/class="account-menu more-group"/);
		expect(src, `${file}: end the "⋯" group with <ReaderSiteLinks>.`).toMatch(
			/<ReaderSiteLinks onpick=\{\(\) => \(moreOpen = false\)\} \/>\s*<\/div>\s*\{\/if\}/
		);
	});

	it('the chapter bar\'s book title links to the book page', () => {
		expect(read(READER)).toMatch(
			/<a\s+href=\{localizeHref\(`\/books\/\$\{slug\}`\)\}[^>]*>[\s\S]{0,120}<bdi class="truncate">\{chapter\.book_title\}<\/bdi><\/a/
		);
	});
});

describe('the chrome bars track the text they belong to', () => {
	// The bars were a flat max-w-3xl (48rem) while the article ranges 27–83rem
	// (measure x scale) and 88rem as a two-column spread — up to 333px wider than
	// the text at the small end, 640px narrower at the large end, matching at no
	// setting a reader can pick.
	it.each([
		{ label: 'reader', file: READER },
		{ label: 'sermon', file: 'routes/sermons/[slug]/+page.svelte' }
	])('$label bar is not pinned to its own fixed width', ({ file }) => {
		const bar = read(file).match(/<div\n?\s*class="mx-auto flex[^"]*"/)?.[0];
		// Assert the bar was FOUND before asserting anything about it — a regex
		// that quietly stops matching would otherwise turn this into a test that
		// passes because it looked at nothing.
		expect(bar, `${file}: could not find the chrome bar's container div.`).toBeDefined();
		expect(bar, `${file}: the reader chrome bar should not carry its own max-w-*.`).not.toMatch(
			/\bmax-w-(?:xl|2xl|3xl|4xl|5xl)\b/
		);
	});

	it('reader bar shares the article width expression', () => {
		// Same source, so the spread case comes along for free.
		expect(read(READER)).toMatch(/const chromeMax = \$derived\(`min\(max\(\$\{articleMax\}, 32rem\), 100%\)`\)/);
	});

	it('sermon bar tracks the reading measure', () => {
		expect(read('routes/sermons/[slug]/+page.svelte')).toMatch(
			/max-width: min\(max\(var\(--reading-measure\), 32rem\), 100%\)/
		);
	});
});

describe('the paged reader clears the nav', () => {
	const src = read(READER);

	it('starts the fixed chrome below the nav', () => {
		expect(
			src,
			'.reader-chrome.fixed must start at var(--appnav-h) — `fixed` measures ' +
				'from the viewport, where the static nav still is.'
		).toMatch(/\.reader-chrome\.fixed\s*\{[^}]*top:\s*var\(--appnav-h/);
	});

	it('starts the paged column below both bars', () => {
		// --pgtop is only the chrome's height; the nav is above that again, and
		// both are viewport-relative here, so they add.
		expect(src).toMatch(/article\.paged\s*\{[^}]*top:\s*calc\(var\(--appnav-h[^)]*\)\s*\+\s*var\(--pgtop/);
	});

	it('still fills the viewport in focus mode', () => {
		// Focus hides both bars; the column should reclaim the whole screen.
		expect(src).toMatch(/article\.paged\.focus\s*\{\s*top:\s*0;/);
	});
});

describe('a Reader under the sticky app nav clears it', () => {
	it('the biography parks a jumped-to paragraph below the nav and its jump-bar', () => {
		// The author route keeps the app nav sticky, but its Reader passed
		// `headerOffset={0}`: a Notebook `?p=` link parked the paragraph under the
		// nav, and "the paragraph at the top" was read against the wrong line.
		const src = read('routes/authors/[slug]/+page.svelte');
		expect(src).not.toMatch(/headerOffset=\{0\}/);
		expect(src).toMatch(/readerUi\.navHeight/);
		expect(read(LAYOUT)).toMatch(/readerUi\.navHeight = navH/);
	});
});

describe('a floating reader control clears the bottom bars', () => {
	it('the floating bookmark sits above the phone tab bar and the Listen bar', () => {
		// It sat at `bottom: 1rem` under the z-40 tab bar, which took the tap.
		const src = read('lib/components/FloatingBookmark.svelte');
		expect(src).toMatch(/var\(--tabbar-h, 0px\)/);
		expect(src).toMatch(/var\(--listenbar-h, 0px\)/);
	});

	it('the feedback "+" sits above the chapter footer and the Listen bar', () => {
		// It sat at `bottom: 1rem` over the phone reader's Listen · Aa · Next row.
		const src = read('lib/components/FeedbackFab.svelte');
		expect(src).toMatch(/var\(--foot-h, 0px\)/);
		expect(src).toMatch(/var\(--listenbar-h, 0px\)/);
	});

	it('the phone reading surfaces carry the feedback "+" in their footer, not floating', () => {
		// Lifted above the footer, the floating "+" sat over the text being read.
		for (const file of [READER, 'routes/sermons/[slug]/+page.svelte']) {
			expect(read(file), file).toMatch(/<div class="foot-actions"[\s\S]*?<FootFeedback \/>/);
		}
	});

	it('the sermon footer matches the chapter footer: scrubber, and Previous/Next in the row', () => {
		const src = read('routes/sermons/[slug]/+page.svelte');
		const row = src.slice(src.indexOf('<div class="foot-actions"'));
		expect(src).toMatch(/class="scrubber"/);
		expect(row).toMatch(/sermon\.prev\.slug[\s\S]*<FootFeedback \/>[\s\S]*sermon\.next\.slug/);
		// FootFeedback (always inside the row) flags <html> while it is mounted,
		// and the floating "+" steps aside on that flag.
		expect(read('lib/components/FootFeedback.svelte')).toMatch(
			/holdFlag\(document\.documentElement, 'data-foot-actions'\)/
		);
		expect(read('lib/components/FeedbackFab.svelte')).toMatch(
			/:root\[data-foot-actions\]\) \.fb-fab/
		);
	});

	it('every page whose header scrolls away bookmarks from the floating control', () => {
		for (const file of ['lib/components/ArticleDetail.svelte', 'routes/authors/[slug]/+page.svelte']) {
			expect(read(file), file).toMatch(/<FloatingBookmark\b/);
		}
	});
});
