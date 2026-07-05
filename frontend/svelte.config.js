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
			// Routes that are prerenderable but legitimately unreached at build:
			// /sermons/[slug] and /plans/[slug] have no pages when their API
			// endpoints have no content (or lag a simultaneous deploy), and
			// /account is only linked at runtime (signed-in header). Any other
			// unseen prerenderable route is still a real error.
			handleUnseenRoutes: ({ routes }) => {
				const expected = new Set(['/sermons/[slug]', '/plans/[slug]', '/account']);
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
