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
		prerender: {
			// /sermons/[slug] is prerenderable but has no pages when the library
			// has no sermons yet — that's expected, not a build failure. Any other
			// unseen prerenderable route is still a real error.
			handleUnseenRoutes: ({ routes }) => {
				const unexpected = routes.filter((id) => id !== '/sermons/[slug]');
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
