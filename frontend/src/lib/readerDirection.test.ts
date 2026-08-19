import { existsSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

// resolve from cwd like href.test.ts, which documents that vitest rewrites
// import.meta.url during transform.
const FRONTEND = [resolve(process.cwd()), resolve(process.cwd(), 'frontend')].find((d) =>
	existsSync(join(d, 'src/lib'))
) as string;

/**
 * `dir="auto"` must sit on the CONTENT, never on a container that also holds
 * localized chrome.
 *
 * The readers mix two directions: breadcrumbs and prev/next follow the UI
 * locale, while the text follows the language the text is actually in. When
 * `dir="auto"` sat on the outer <article>, it resolved from the first strong
 * character in that element — the localized breadcrumb. Under /ar that is
 * Arabic, so English book text inherited RTL and sentence-final punctuation
 * rendered at the start of the line (".and defects await the creature").
 *
 * `auto` (rather than a `dir` derived from the content's language) is
 * deliberate: `localized()` silently falls back to English when a translation
 * is missing, so a language-derived direction would render that English RTL —
 * the very bug this fixes. Reading the actual bytes is correct through the
 * fallback. Known tradeoff: `auto` resolves from the FIRST strong character, so
 * an Arabic chapter opening with a Latin epigraph resolves LTR.
 *
 * SCOPE, honestly: this pins the KNOWN content surfaces below. It cannot catch
 * a NEW surface that renders content without `dir="auto"`. If a third reading
 * surface appears, add it here — or extract a component that owns `dir="auto"`
 * so it comes for free.
 *
 * That extraction has now happened for the prose: `Reader.svelte` owns the
 * `.reading` element, so every surface built on it gets `dir="auto"` without
 * being listed. The chapter reader still renders its body inline and is pinned
 * separately below until it migrates. Each page keeps its own `<article>` and
 * `<h1>`, so those assertions stay per-page.
 */
const READERS = [
	'src/routes/books/[slug]/[order]/+page.svelte',
	'src/routes/sermons/[slug]/+page.svelte'
];

/** Files that render a `.reading` body themselves and must carry the dir. */
const PROSE_OWNERS = [
	'src/lib/components/Reader.svelte',
	// Not yet migrated onto <Reader>; drop when it is.
	'src/routes/books/[slug]/[order]/+page.svelte'
];

/**
 * Other surfaces rendering content inside localized chrome: [file, anchor].
 *
 * The author page used to be pinned here on `bind:this={bioEl}`. Its biography
 * now renders through <Reader>, which is covered by PROSE_OWNERS above — so the
 * guarantee is inherited rather than restated, which is the point of the
 * extraction. Re-adding it would pin a line that no longer carries the dir.
 */
const CONTENT_SURFACES: [path: string, needle: string][] = [
	['src/routes/books/[slug]/+page.svelte', '{book.title}</h1>'],
	['src/routes/books/[slug]/+page.svelte', '{ch.title}</span>']
];

const read = (path: string) => readFileSync(join(FRONTEND, path), 'utf8');

describe('reader text direction', () => {
	for (const path of READERS) {
		it(`${path}: <article> does not carry dir`, () => {
			// Anchored to line start: an unanchored /<article[^>]*>/ also matches the
			// string "<article>" inside a CSS comment further down the file, which
			// let a renamed tag pass silently.
			const article = read(path).match(/^\s*<article[^>]*>/m)?.[0];
			// Assert it was FOUND first: `?? ''` would sail past a rename or an
			// extraction into a component — failing open on the assertion that
			// matters most here.
			expect(article, 'no <article> found — did the reader markup change?').toBeTruthy();
			expect(article).not.toMatch(/\bdir=/);
		});

		it(`${path}: title carries dir="auto"`, () => {
			// Assert on the whole source rather than capturing the tag: an inline
			// arrow handler (onclick={() => f()}) contains '>' and would truncate a
			// [^>]* capture — spurious failures, or worse a spurious pass.
			expect(read(path), 'title dir="auto"').toMatch(/<h1[^>]*\sdir="auto"/);
		});
	}

	for (const path of PROSE_OWNERS) {
		it(`${path}: reading body carries dir="auto"`, () => {
			// Match the class LIST, not a bare closing quote: Reader takes a `class`
			// prop (for surfaces with their own band width), so `class="reading"`
			// becomes `class="reading …"` and a stricter regex would fail this open.
			//
			// `\s[^>]*` rather than a literal space before `class`: the tag is
			// formatted across several lines once it carries enough attributes, and
			// requiring `<div class=` on one line failed a body that did have the
			// dir. `[^>]` cannot cross the tag's own `>`, so this still can't drift
			// onto a later element.
			expect(read(path), 'reading body dir="auto"').toMatch(
				/<div\s[^>]*class="reading[^"]*"[^>]*\sdir="auto"/
			);
		});
	}

	for (const [path, needle] of CONTENT_SURFACES) {
		it(`${path}: "${needle}" carries dir="auto"`, () => {
			const line = read(path)
				.split('\n')
				.find((l) => l.includes(needle));
			expect(line, `"${needle}" not found — markup changed?`).toBeTruthy();
			expect(line).toMatch(/dir="auto"/);
		});
	}
});
