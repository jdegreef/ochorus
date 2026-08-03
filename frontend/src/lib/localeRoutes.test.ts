import { existsSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * Every configured UI locale must have its index-page rewrites in render.yaml.
 *
 * Render's route matcher has no wildcard for the locale segment, so each locale
 * repeats the same block. That list is hand-maintained and drifted twice: /pt
 * and /ar were both wired as full locales — message catalogs, locale registry,
 * sitemap entries — while render.yaml still only knew es/sw/lg. The pages were
 * built and sitemapped, and every one of them served the 4 KB SPA shell to
 * crawlers. 166 Portuguese URLs were advertised to Google that way.
 *
 * Nothing else catches it: the build succeeds, the tests pass, the pages exist
 * on disk, and the only symptom is a 4 KB response to a crawler nobody watches.
 */
const ROOT = [resolve(process.cwd(), '..'), resolve(process.cwd())].find((d) =>
	existsSync(join(d, 'render.yaml'))
) as string;
const FRONTEND = [resolve(process.cwd()), resolve(process.cwd(), 'frontend')].find((d) =>
	existsSync(join(d, 'project.inlang/settings.json'))
) as string;

const RENDER_YAML = readFileSync(join(ROOT, 'render.yaml'), 'utf8');
const LOCALES: string[] = JSON.parse(
	readFileSync(join(FRONTEND, 'project.inlang/settings.json'), 'utf8')
).locales.filter((l: string) => l !== 'en');

/** Prerendered index pages that need an explicit rewrite per locale. */
const INDEX_PAGES = [
	'books',
	'biographies',
	'about',
	'contact',
	'legal',
	'sermons',
	'plans',
	'topics',
	// Added after /search prerendered but had no rewrite at all — not for the
	// locales and not for the base path either, so the built search.html was
	// unreachable and the page served the 4 KB shell (#725, fixed in #726).
	'search'
];

describe('render.yaml locale routes', () => {
	it('covers every configured locale', () => {
		const missing = LOCALES.filter((l) => !RENDER_YAML.includes(`source: /${l}\n`));
		expect(missing, 'locales with no landing-page rewrite').toEqual([]);
	});

	// The base (unprefixed) path needs its own rewrite too. This was the hole
	// /search fell through: the per-locale loop below would have caught a missing
	// /es/search, but nothing asserted /search itself — and both were absent.
	it('covers the base path for every index page', () => {
		const missing = INDEX_PAGES.filter((p) => !RENDER_YAML.includes(`source: /${p}\n`));
		expect(missing, 'index pages with no base-path rewrite').toEqual([]);
	});

	for (const page of INDEX_PAGES) {
		it(`covers /<locale>/${page} for every locale`, () => {
			const missing = LOCALES.filter((l) => !RENDER_YAML.includes(`source: /${l}/${page}\n`));
			expect(missing, `locales missing /${page}`).toEqual([]);
		});
	}

	it('rewrites every locale to its own .html, never another locale’s', () => {
		for (const l of LOCALES) {
			const re = new RegExp(`source: /${l}(/[a-z-]+)?\\n\\s*destination: (/[^\\n]+)`, 'g');
			for (const m of RENDER_YAML.matchAll(re)) {
				expect(m[2], `source /${l}${m[1] ?? ''}`).toMatch(new RegExp(`^/${l}[./]`));
			}
		}
	});
});

/**
 * Legacy URLs from the domain's WordPress era that are STILL RANKING.
 *
 * Found in Search Console on 2026-08-02: 33 of the site's first 47 impressions
 * went to old-site URLs rather than to Ochorus, and the ones without a
 * redirect answered 200 with the 4 KB SPA shell — a searcher clicking through
 * landed on a blank page. `/ochorus-books/` alone out-impressed the homepage.
 *
 * These rules are easy to drop in a render.yaml edit and impossible to notice
 * afterwards, because the symptom is a 200 rather than an error.
 */
describe('render.yaml legacy redirects', () => {
	const LEGACY: [string, string][] = [
		['/author-biographies', '/biographies'],
		['/ochorus-books', '/books'],
		['/about-us', '/about'],
		['/home', '/'],
		['/books/a-king-in-a-manger-2', '/books'],
		['/books/grace-for-grace-2', '/books']
	];

	for (const [from, to] of LEGACY) {
		it(`301s ${from} -> ${to}`, () => {
			// Both slash forms are listed in render.yaml; assert the rule exists
			// and points where we intend.
			const rule = new RegExp(
				`source: ${from.replace(/\//g, '\\/')}\\/?\\n\\s*destination: ${to.replace(/\//g, '\\/')}\\n`
			);
			expect(rule.test(RENDER_YAML), `no redirect from ${from}`).toBe(true);
		});
	}
});
