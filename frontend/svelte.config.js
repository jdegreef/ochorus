import adapter from '@sveltejs/adapter-static';

import { readFileSync } from 'node:fs';

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
			handleUnseenRoutes: ({ routes }) => {
				const expected = new Set([
					'/sermons/[slug]',
					'/plans/[slug]',
					'/topics/[slug]',
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
