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
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

// Resolve from the working directory (vitest runs with cwd = frontend/, as CI
// does) rather than import.meta.url, which vitest rewrites during transform —
// that silently made this guard skip, which is worse than not having it.
const BUILD = [resolve(process.cwd(), 'build'), resolve(process.cwd(), 'frontend/build')].find(existsSync) ?? '';
const BARE_DETAIL = /href="(?:\/(?:es|sw|lg))?\/(?:books|authors|topics|sermons|plans)\/[^"/.]+(?:\/[^"/.]+)?"/g;

function htmlFiles(dir: string, out: string[] = []): string[] {
	for (const e of readdirSync(dir)) {
		const p = join(dir, e);
		if (statSync(p).isDirectory()) htmlFiles(p, out);
		else if (e.endsWith('.html')) out.push(p);
	}
	return out;
}

describe.skipIf(!BUILD)('built output', () => {
	// Prose served by the API can also contain a hand-written link, and the build
	// fetches that prose from PRODUCTION — so a content fix only clears this once
	// the backend has deployed it. Migration 0054 fixes the one instance; drop
	// this entry (and the migration stays as history) after that deploy.
	const CONTENT_PENDING_DEPLOY = ['href="/authors/susanna-wesley"'];

	it('contains no bare (non-slash) detail-route links', () => {
		const offenders: string[] = [];
		for (const f of htmlFiles(BUILD)) {
			const hits = (readFileSync(f, 'utf8').match(BARE_DETAIL) ?? []).filter(
				(h) => !CONTENT_PENDING_DEPLOY.includes(h)
			);
			if (hits.length) offenders.push(`${f.replace(BUILD, '')}: ${[...new Set(hits)].join(', ')}`);
		}
		expect(offenders).toEqual([]);
	});
});
