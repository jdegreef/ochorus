import adapter from '@sveltejs/adapter-static';

import { readFileSync } from 'node:fs';

import { cspDirectives } from './csp.config.js';

/**
 * connect-src, plus the API origin THIS build actually talks to.
 *
 * The CSP now ships baked into the built pages (a <meta>), so it is enforced
 * wherever the build runs — including the CI browser-smoke job, which drives the
 * built app against a local backend on http://localhost:8000. csp.config.js lists
 * only the production hosts (and must: csp.test.ts forbids http:// and localhost
 * in the shipped policy), so without this every API fetch in CI/local preview is
 * blocked by connect-src. PUBLIC_API_BASE_URL is the origin the build dials — in
 * production it is https://api.ochorus.com (already listed → deduped); in CI/local
 * it is the localhost backend. Adding it here (not in csp.config.js) keeps the
 * shipped-prod assertions clean while letting the app reach its own API anywhere.
 */
function directivesForThisBuild() {
	const base = process.env.PUBLIC_API_BASE_URL;
	let origin;
	try {
		origin = base ? new URL(base).origin : '';
	} catch {
		origin = '';
	}
	const connect = cspDirectives['connect-src'];
	if (!origin || connect.includes(origin)) return cspDirectives;
	return { ...cspDirectives, 'connect-src': [...connect, origin] };
}

/** Non-English UI locales, read from the inlang project (the source of truth). */
const LOCALES = JSON.parse(
	readFileSync(new URL('./project.inlang/settings.json', import.meta.url), 'utf8')
).locales.filter((l) => l !== 'en');

/** @type {import('@sveltejs/kit').Config} */
const config = {
	compilerOptions: {
		// Force runes mode except for node_modules libraries.
		runes: ({ filename }) =>
			filename.split(/[/\\]/).includes('node_modules') ? undefined : true
	},
	kit: {
		// Static SPA: serve the app shell for every route via the 200.html
		// fallback. (SEO prerendering can be added later for the web target.)
		adapter: adapter({ fallback: '200.html' }),
		paths: { relative: false },
		// Content-Security-Policy in `hash` mode: SvelteKit computes the hash of
		// each inline script it emits (the per-build bootstrap) at build time and
		// injects the policy as a <meta> on every prerendered page + the 200.html
		// fallback. This is what lets `script-src` drop `'unsafe-inline'`. The
		// directives (and the rationale) live in ./csp.config.js — a plain-data
		// module so src/lib/csp.test.ts can assert them without running this file.
		// connect-src also picks up this build's own PUBLIC_API_BASE_URL origin
		// (see directivesForThisBuild) so the app can reach its API in CI/local.
		csp: { mode: 'hash', directives: directivesForThisBuild() },
		// We register src/service-worker.ts ourselves (see lib/pwa.svelte.ts) so we
		// can surface an "update available" prompt instead of updating silently.
		serviceWorker: { register: false },
		prerender: {
			// A prerendered page that errors still fails the build — never ship a
			// half-broken page — but the default message buries the diagnosis. Say
			// what died and where, and point at the build-time retry layer: apiFetch
			// already retries 5xx/network blips during prerender (see $lib/api.ts),
			// so an error surviving to here is persistent, not a flaky deploy.
			handleHttpError: ({ status, path, referrer, message }) => {
				throw new Error(
					`Prerender got ${status} on ${path}` +
						(referrer ? ` (linked from ${referrer})` : '') +
						`: ${message}\n` +
						'apiFetch already retried transient API failures during the build, ' +
						'so this page is persistently broken — check the API response for ' +
						'its data before re-deploying.'
				);
			},
			// The crawler only follows links from the live index pages, so
			// unpublished books/authors are dropped from the prerendered set on the
			// next build (a backend-only unpublish doesn't rebuild the web service —
			// force one; see the deploy skill, gotcha #2). 2026-07-10.
			// Seed the crawler with each locale's landing page + localized index
			// pages. From these it follows the localizeHref() links to discover the
			// localized dynamic pages (/es/books/<slug>, /es/authors/<slug>, …).
			// English pages are covered by the default '*' crawl from '/'.
			entries: [
				'*',
				// Derived from the inlang project — the same file the Paraglide
				// runtime compiles from — so a new locale is crawled the moment it is
				// registered. Hardcoding this list is how /pt and /ar shipped with no
				// prerendered pages at all: navigable, in the sitemap, serving the SPA
				// shell to crawlers.
				...LOCALES.flatMap((l) => [
					`/${l}`,
					`/${l}/books`,
					`/${l}/biographies`,
					// The CRAWL ANCHOR, and it has to be seeded explicitly because
					// nothing links to it. /biographies paginates client-side (24 of 35
					// writers reached the built HTML) and its era links live behind a
					// client-side sort state (so no built page in any locale carried
					// one), which left 49 sitemap URLs served as the SPA shell and
					// reported by Search Console as "Excluded by 'noindex'".
					// /authors carries the full link set; see its +page.svelte.
					`/${l}/authors`,
					`/${l}/sermons`,
					`/${l}/plans`,
					`/${l}/topics`,
					`/${l}/about`,
					`/${l}/contact`
				])
			],
			// Routes that are prerenderable but legitimately unreached at build:
			// /sermons/[slug], /plans/[slug] and /topics/[slug] have no pages when
			// their API endpoints have no content (or lag a simultaneous deploy),
			// and /account is only linked at runtime (signed-in header). Any other
			// unseen prerenderable route is still a real error.
			//
			// The two /scripture detail routes are the same case with a sharper
			// edge: their pages exist only where `ChapterCitation` has rows, and
			// citations are indexed by the `index_citations` RELEASE step — not by
			// `seed_if_empty`. So a build against a freshly seeded database (CI
			// does exactly this, and so does a first deploy) legitimately finds no
			// scripture page to render, and must not fail for it. The pages appear
			// on the next build after the release chain has run.
			handleUnseenRoutes: ({ routes }) => {
				const expected = new Set([
					'/sermons/[slug]',
					'/plans/[slug]',
					'/topics/[slug]',
					// Articles have no pages until the articles API serves content
					// (or when the web build lags the backend deploy that adds it) —
					// same case as /sermons/[slug]. The index still prerenders.
					'/articles/[slug]',
					'/scripture/[book]/[chapter]',
					'/scripture/[book]/[chapter]/[verse]',
					// Quote pages exist only for an author whose quotations a
					// person has approved. Until `approve_quotes` runs there are
					// none, which is the correct state — not a broken build.
					'/quotes/[author]',
					'/account'
				]);
				const unexpected = routes.filter((id) => !expected.has(id));
				if (unexpected.length) {
					throw new Error(
						'Prerenderable routes were never reached:\n' +
							unexpected.map((r) => `  - ${r}`).join('\n')
					);
				}
			}
		}
	}
};

export default config;
