/**
 * Every URL the sitemap advertises must exist as a prerendered file.
 *
 * The static adapter serves `200.html` for any path with no prerendered file,
 * and `+error.svelte` marks that shell `noindex` on purpose (otherwise a stale
 * URL gets indexed as a soft-404 duplicate). So an advertised-but-unprerendered
 * URL does not degrade gracefully — Google is told the page exists, fetches it,
 * finds `noindex`, and drops it. The sitemap becomes a list of promises the
 * site does not keep.
 *
 * Nothing caught that, because each half is individually correct: the sitemap
 * enumerates content from the API, and prerendering discovers localized pages
 * by CRAWLING links (only 8 paths per locale are seeded; see svelte.config.js).
 * The gap between them is invisible until Search Console reports it weeks later.
 * It has bitten twice:
 *
 *   * /pt and /ar shipped with no prerendered pages at all — navigable, in the
 *     sitemap, serving the shell to crawlers (the note in svelte.config.js).
 *   * 49 URLs — every localized `biographies/era/<id>`, and the localized pages
 *     of 8 writers with no published works — because /biographies paginates
 *     client-side at 24 and its era links sit behind a client-side sort state.
 *     Both classes were reachable from no built page in any locale.
 *
 * This is the CI-safe counterpart to `scripts/check-slashes.mjs`, which probes a
 * deployed host: that one answers "is the canonical URL served correctly?", this
 * one answers "was it built at all?".
 *
 * SINCE THE SITEMAP SPLIT this has to walk an index. `sitemap.xml` is a
 * `<sitemapindex>` whose `<loc>`s name child sitemaps — which are all real
 * built files, so a guard that checked them directly would pass while
 * inspecting no page at all, and go on passing however many chapter URLs went
 * missing. Silently disarming this test would be a worse outcome than the two
 * incidents it was written for, so the URLs are collected from the children and
 * the index is asserted to actually have some.
 *
 * Skipped when there is no build/ — `npm run test` is run without one locally.
 */
import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';

// Resolve from the working directory (vitest runs with cwd = frontend/, as CI
// does) rather than import.meta.url, which vitest rewrites during transform —
// the same trap that silently disabled the href guard.
const BUILD =
	[
		resolve(process.cwd(), 'build'),
		resolve(process.cwd(), 'frontend/build')
	].find(existsSync) ?? '';
const SITEMAP = BUILD ? join(BUILD, 'sitemap.xml') : '';

/**
 * A prerendered page lands as `<path>/index.html` when its route sets
 * `trailingSlash = 'always'` and as `<path>.html` otherwise. Accept either:
 * which one a route uses is that route's business, not this guard's.
 */
function isPrerendered(pathname: string): boolean {
	const p = pathname.replace(/^\/+|\/+$/g, '');
	if (!p) return existsSync(join(BUILD, 'index.html'));
	return (
		existsSync(join(BUILD, p, 'index.html')) ||
		existsSync(join(BUILD, `${p}.html`))
	);
}

/** Every `<loc>` in an XML sitemap document. */
const locsIn = (xml: string): string[] =>
	[...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);

/** A built sitemap file, by the pathname its `<loc>` advertises. */
const readSitemap = (pathname: string): string | null => {
	const file = join(BUILD, pathname.replace(/^\/+/, ''));
	return existsSync(file) ? readFileSync(file, 'utf8') : null;
};

describe.skipIf(!BUILD || !existsSync(SITEMAP))('prerender coverage', () => {
	it('prerenders every URL the sitemap advertises', () => {
		const root = readFileSync(SITEMAP, 'utf8');
		const isIndex = root.includes('<sitemapindex');
		const children = isIndex ? locsIn(root) : [];

		// The index has to link something. An index over nothing is the shape
		// this guard would otherwise read as "no missing pages".
		if (isIndex) expect(children.length).toBeGreaterThan(0);

		// A child named in the index but absent from the build is the same broken
		// promise as a missing page, one level up — name them rather than
		// silently collecting no URLs from them.
		const missingChildren = children.filter(
			(u) => readSitemap(new URL(u).pathname) === null
		);
		expect(missingChildren.map((u) => new URL(u).pathname)).toEqual([]);

		const urls = [
			...new Set(
				isIndex
					? children.flatMap((u) =>
							locsIn(readSitemap(new URL(u).pathname) ?? '')
						)
					: locsIn(root)
			)
		];

		// A sitemap that lost its content would vacuously pass, and this guard is
		// most valuable exactly when a build goes wrong.
		expect(urls.length).toBeGreaterThan(100);

		const missing = urls.filter((u) => !isPrerendered(new URL(u).pathname));
		// Report the paths, not the count: the failure is only actionable if you
		// can see which class of page went missing.
		expect(missing.map((u) => new URL(u).pathname)).toEqual([]);
	});
});
