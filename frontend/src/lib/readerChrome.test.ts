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
 * These are source-shape checks, not rendering checks — they can't see a
 * stacking context. What they CAN do is fail when the two invariants that make
 * the collision impossible get reverted by someone who doesn't know the story.
 */

const SRC = join(import.meta.dirname, '..');
const read = (file: string) => readFileSync(join(SRC, file), 'utf8');

const LAYOUT = 'routes/+layout.svelte';
const READER = 'routes/books/[slug]/[order]/+page.svelte';

describe('the layout publishes the nav height as a fact', () => {
	it('does not zero --appnav-h on the reading routes', () => {
		// It used to be `inReader ? 0 : navH`. True only in scroll mode, where the
		// static nav rides away — and page mode is the case that doesn't scroll.
		const decl = read(LAYOUT).match(/--appnav-h:\s*\{([^}]*)\}/)?.[1] ?? '';
		expect(decl, '--appnav-h must be declared from a value, not omitted').not.toEqual('');
		expect(
			decl,
			'--appnav-h is the nav\'s rendered height, not a policy about who clears ' +
				'it. Zeroing it in the reader is what put the page-turn bar under the nav.'
		).not.toMatch(/inReader/);
	});

	it('reports 0 only when the nav is genuinely not rendered', () => {
		// Focus mode removes the nav from the DOM, so 0 is the truth there.
		expect(read(LAYOUT)).toMatch(/--appnav-h:\s*\{readerUi\.focus \? 0 : navH\}px/);
	});

	it('seeds navH synchronously before observing it', () => {
		// A ResizeObserver's first callback lands a frame late; without the
		// synchronous read the bar rendered at 0 for that frame and then jumped.
		const src = read(LAYOUT);
		const effect = src.slice(src.indexOf('let navH'), src.indexOf('ro.observe(navEl)'));
		expect(
			effect,
			'measure navEl once directly, before the ResizeObserver, or the reader bar jumps on load.'
		).toMatch(/navH = Math\.round\(navEl\.getBoundingClientRect\(\)\.height\)/);
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
