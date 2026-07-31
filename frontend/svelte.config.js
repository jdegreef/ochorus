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
		// Static SPA fallback. VERIFICATION SPIKE (#3 soft-404): renamed from
		// 200.html to 404.html to test whether Render serves a root 404.html with
		// an HTTP 404 status for unmatched paths (the file content is identical —
		// the full app shell either way). If it does, unknown URLs stop being
		// soft-404s. Paired with removing the /* -> /200.html catch-all in
		// render.yaml. Do NOT merge until a preview confirms the behaviour and the
		// client-only routes get explicit shell rewrites.
		adapter: adapter({ fallback: '404.html' }),
		paths: { relative: false },
		// We register src/service-worker.ts ourselves (see lib/pwa.svelte.ts) so we
		// can surface an "update available" prompt instead of updating silently.
		serviceWorker: { register: false },
		prerender: {
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
