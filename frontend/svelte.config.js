import adapter from '@sveltejs/adapter-static';

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
				...['es', 'sw', 'lg'].flatMap((l) => [
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
