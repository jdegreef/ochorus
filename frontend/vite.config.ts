import fs from 'node:fs';
import path from 'node:path';
import { paraglideVitePlugin } from '@inlang/paraglide-js';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig, type Plugin } from 'vite';
import { APP } from './app-target.js';

/**
 * Force absolute `/_app/immutable/…` URLs in client JS chunks.
 *
 * Vite emits the CSS/JS preload manifest as path-relative `./_app/immutable/…`,
 * which the browser resolves against the importing module and produces a
 * doubled-prefix 404 that crashes hydration on static builds. SvelteKit's
 * `paths.relative:false` is meant to prevent this but Vite ignores the `false`
 * case, so we post-process the chunks. (Carried over from Take Root.)
 *
 * LENGTH-PRESERVING, because the rewrite runs after the source maps are made
 * (scripts/sentry-sourcemaps.mjs uploads them). Dropping the "." shortens the
 * file by one character per occurrence, and these chunks are one long line
 * with the deps list near the start, so every later column would point a
 * character early and Sentry would name the wrong code. Each quoted literal
 * gets its spare character back as a space after the closing quote, which is
 * legal anywhere a string token is. An occurrence that is not a whole quoted
 * literal falls back to the plain replace.
 */
const RELATIVE_LITERAL = /(["'`])\.\/_app\/immutable\/([^"'`]*)\1/g;
const absoluteAssetUrls = (): Plugin => ({
	name: 'absolute-immutable-asset-urls',
	apply: 'build',
	enforce: 'post',
	closeBundle() {
		const root = path.resolve(__dirname, '.svelte-kit/output/client/_app/immutable');
		if (!fs.existsSync(root)) return;
		const walk = (dir: string) => {
			for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
				const p = path.join(dir, entry.name);
				if (entry.isDirectory()) walk(p);
				else if (entry.name.endsWith('.js')) {
					const code = fs.readFileSync(p, 'utf8');
					if (code.includes('./_app/immutable/')) {
						fs.writeFileSync(
							p,
							code
								.replace(RELATIVE_LITERAL, '$1/_app/immutable/$2$1 ')
								.replaceAll('./_app/immutable/', '/_app/immutable/')
						);
					}
				}
			}
		};
		walk(root);
	}
});

/**
 * The native app's build (scripts/build-app.mjs) prerenders nothing — but
 * SvelteKit still calls every route's `entries()` while analysing the build,
 * and those ask the live API for the slugs to prerender. Un-exporting them in
 * that build alone keeps it offline and independent of the API; the website's
 * build is untouched. Route modules only, and only the `entries` export.
 */
const ROUTE_MODULE = /[\\/]src[\\/]routes[\\/].*\+(page|server)\.[jt]s$/;
const ENTRIES_EXPORT = /^export (const|let|async function|function) entries\b/m;
const appSkipsEntries = (): Plugin => ({
	name: 'app-skips-prerender-entries',
	apply: 'build',
	transform(code, id) {
		if (!ROUTE_MODULE.test(id) || !ENTRIES_EXPORT.test(code)) return null;
		return { code: code.replace(ENTRIES_EXPORT, '$1 entries'), map: null };
	}
});

export default defineConfig(({ isSsrBuild }) => ({
	plugins: [
		tailwindcss(),
		// Compiles messages/*.json into $lib/paraglide and provides the URL-locale
		// runtime (localizeHref/deLocalizeUrl). URL prefix wins, then cookie, then
		// the English base locale. Must run before sveltekit().
		paraglideVitePlugin({
			project: './project.inlang',
			outdir: './src/lib/paraglide',
			strategy: ['url', 'cookie', 'baseLocale']
		}),
		...(APP ? [appSkipsEntries()] : []),
		sveltekit(),
		absoluteAssetUrls()
	],
	build: {
		// Source maps only for a build that will upload them to Sentry, and
		// 'hidden' (no `//# sourceMappingURL`), so a browser never asks for one.
		// scripts/sentry-sourcemaps.mjs uploads them and deletes them from build/.
		// Client build only: the server/prerender build never ships, and its maps
		// would only add time to a deploy.
		sourcemap: process.env.SENTRY_AUTH_TOKEN && !isSsrBuild ? 'hidden' : false
	},
	define: {
		/**
		 * The commit this bundle was built from, baked in so a browser error can
		 * name its release.
		 *
		 * Injected here rather than read through `$env` because it is not a public
		 * runtime setting: the static site is built once per deploy and served
		 * from a CDN, so the value is fixed at build time and there is no server
		 * left to read an env var at request time.
		 *
		 * Render sets RENDER_GIT_COMMIT during every build. Locally and in CI it
		 * is unset, which yields '' — Sentry then sends no release rather than a
		 * wrong one.
		 */
		__RELEASE__: JSON.stringify(process.env.RENDER_GIT_COMMIT ?? ''),
		/**
		 * Whether this bundle is the native app's (Capacitor, iOS + Android)
		 * rather than the website's. Set by scripts/build-app.mjs; read through
		 * `IS_APP` in $lib/platform, never directly. A build-time constant so the
		 * web bundle drops the app-only branches entirely.
		 */
		__APP__: JSON.stringify(APP)
	}
}));
