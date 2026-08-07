import { describe, expect, it } from 'vitest';
import { withTrailingSlash } from './href';

describe('withTrailingSlash', () => {
	it('adds the slash to detail pages, which is the whole point', () => {
		expect(withTrailingSlash('/books/the-inner-chamber')).toBe('/books/the-inner-chamber/');
		expect(withTrailingSlash('/authors/andrew-murray')).toBe('/authors/andrew-murray/');
		expect(withTrailingSlash('/topics/prayer')).toBe('/topics/prayer/');
		expect(withTrailingSlash('/sermons/free-grace')).toBe('/sermons/free-grace/');
		expect(withTrailingSlash('/plans/humility')).toBe('/plans/humility/');
	});

	it('handles the chapter route (one segment deeper)', () => {
		expect(withTrailingSlash('/books/the-inner-chamber/12')).toBe('/books/the-inner-chamber/12/');
	});

	it('keeps the locale prefix and still matches the shape', () => {
		expect(withTrailingSlash('/es/books/the-inner-chamber')).toBe('/es/books/the-inner-chamber/');
		expect(withTrailingSlash('/sw/authors/andrew-murray')).toBe('/sw/authors/andrew-murray/');
		expect(withTrailingSlash('/lg/books/humility/3')).toBe('/lg/books/humility/3/');
	});

	it('is idempotent — never doubles the slash', () => {
		expect(withTrailingSlash('/books/humility/')).toBe('/books/humility/');
		expect(withTrailingSlash(withTrailingSlash('/books/humility'))).toBe('/books/humility/');
	});

	it('preserves query strings and hashes, slash before them', () => {
		expect(withTrailingSlash('/books/humility?from=home')).toBe('/books/humility/?from=home');
		expect(withTrailingSlash('/books/humility#chapter-2')).toBe('/books/humility/#chapter-2');
		expect(withTrailingSlash('/search?q=prayer')).toBe('/search?q=prayer');
	});

	it('leaves index pages alone — they resolve either way via Render rewrites', () => {
		expect(withTrailingSlash('/books')).toBe('/books');
		expect(withTrailingSlash('/biographies')).toBe('/biographies');
		expect(withTrailingSlash('/es/books')).toBe('/es/books');
		expect(withTrailingSlash('/')).toBe('/');
	});

	it('leaves non-detail and client-only routes alone', () => {
		expect(withTrailingSlash('/admin/books/humility')).toBe('/admin/books/humility');
		expect(withTrailingSlash('/settings')).toBe('/settings');
		expect(withTrailingSlash('/notebook')).toBe('/notebook');
	});

	it('never touches files or external links', () => {
		expect(withTrailingSlash('/covers/humility.svg')).toBe('/covers/humility.svg');
		expect(withTrailingSlash('/books/humility/cover.jpg')).toBe('/books/humility/cover.jpg');
		expect(withTrailingSlash('https://example.com/books/x')).toBe('https://example.com/books/x');
		expect(withTrailingSlash('mailto:support@ochorus.com')).toBe('mailto:support@ochorus.com');
		expect(withTrailingSlash('#era-early')).toBe('#era-early');
	});

	it('ignores paths deeper than the known shapes', () => {
		expect(withTrailingSlash('/books/a/b/c')).toBe('/books/a/b/c');
	});
});

/**
 * The guard that would have caught this bug in the first place.
 *
 * `withTrailingSlash` being correct does not prove the SITE is correct — a link
 * only benefits if it is actually routed through the wrapper, and a URL can also
 * be hand-written in prose (one was: an author bio cross-linked another author
 * without the slash). Asserting on the built HTML tests the property we actually
 * care about, independent of how any given link is constructed.
 *
 * Skipped when there is no build/ — `npm run test` is run without one locally.
 */
import { locales } from '$lib/paraglide/runtime';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';

// Resolve from the working directory (vitest runs with cwd = frontend/, as CI
// does) rather than import.meta.url, which vitest rewrites during transform —
// that silently made this guard skip, which is worse than not having it.
const BUILD = [resolve(process.cwd(), 'build'), resolve(process.cwd(), 'frontend/build')].find(existsSync) ?? '';
// Locales are DERIVED, never hardcoded. This listed es|sw|lg, and when
// Portuguese was wired in as a fifth locale the guard silently stopped covering
// /pt/ — a guard that quietly narrows is the very failure this change exists to
// prevent.
const LOCALE_PREFIX = locales.filter((l) => l !== 'en').join('|');
const BARE_DETAIL = new RegExp(
	`href="(?:/(?:${LOCALE_PREFIX}))?/(?:books|authors|topics|sermons|plans)/[^"/.]+(?:/[^"/.]+)?"`,
	'g'
);

// `withFileTypes` rather than a `statSync` per entry: the directory read
// already knows what each entry is, and asking again costs a syscall per file.
// Over the built site (~2,450 HTML files, climbing with the library) the walk
// measured 1,000ms against 35ms — a 29x difference, and a fifth of the old 5s
// budget burned before a single file was read. Not the whole flake story on its
// own (see the timeout note below), but there is no reason to pay it. Same
// pattern as langChoice.test.ts.
function htmlFiles(dir: string, out: string[] = []): string[] {
	for (const e of readdirSync(dir, { withFileTypes: true })) {
		const p = join(dir, e.name);
		if (e.isDirectory()) htmlFiles(p, out);
		else if (e.name.endsWith('.html')) out.push(p);
	}
	return out;
}

describe.skipIf(!BUILD)('built output', () => {
	// Covers prose as well as components: the build pulls author and book prose
	// from the API, so a hand-written link in a biography is caught here exactly
	// like one in a template. That is how the Swahili and Luganda copies of the
	// John Wesley cross-link were found (ochorus#466).
	// The load-bearing half of the flake fix. Reading and matching the built
	// HTML — ~87MB across ~2,450 files — costs about 0.4s against a warm page
	// cache and about 8s against a cold one, so the default 5s was a cliff the
	// faster walk above does NOT clear on its own: the first run on a fresh
	// checkout or a CI runner is the cold case, every time.
	//
	// Unlike every other test here this one's cost scales with the LIBRARY (one
	// page per work per locale), so it also gets slower as the project succeeds,
	// while competing for disk with 40 other test files in parallel. 30s is well
	// clear of the cold measurement and still fails loudly on a genuine hang.
	it('contains no bare (non-slash) detail-route links', { timeout: 30_000 }, () => {
		const offenders: string[] = [];
		for (const f of htmlFiles(BUILD)) {
			const hits = readFileSync(f, 'utf8').match(BARE_DETAIL);
			if (hits) offenders.push(`${f.replace(BUILD, '')}: ${[...new Set(hits)].join(', ')}`);
		}
		expect(offenders).toEqual([]);
	});
});
