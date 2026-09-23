import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { paraglideVitePlugin } from '@inlang/paraglide-js';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig, type Plugin } from 'vite';

/**
 * Force absolute `/_app/immutable/…` URLs in client JS chunks.
 *
 * Vite emits the CSS/JS preload manifest as path-relative `./_app/immutable/…`,
 * which the browser resolves against the importing module and produces a
 * doubled-prefix 404 that crashes hydration on static builds. SvelteKit's
 * `paths.relative:false` is meant to prevent this but Vite ignores the `false`
 * case, so we post-process the chunks. (Carried over from Take Root.)
 */
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
						fs.writeFileSync(p, code.replaceAll('./_app/immutable/', '/_app/immutable/'));
					}
				}
			}
		};
		walk(root);
	}
});

/**
 * A fingerprint of the SET of cover files — their paths, not their bytes.
 *
 * The reader's resume cache (`$lib/resumeBooks`) keeps a few books' cover
 * URLs between visits, and must not draw one a deploy has moved: a plate that
 * became a painting changes its `cover_url` (`/covers/x.svg` →
 * `/covers/art/x.jpg`), and that always adds or removes a file here. A redraw
 * at the SAME path needs nothing — the browser simply loads the new file — so
 * bytes are deliberately left out. Keyed on this rather than on the build, the
 * cache survives the ~30 deploys a day that touch no cover at all.
 */
function coversVersion(): string {
	const root = path.resolve(__dirname, 'static/covers');
	const files: string[] = [];
	const walk = (dir: string) => {
		for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
			const p = path.join(dir, entry.name);
			if (entry.isDirectory()) walk(p);
			else files.push(path.relative(root, p));
		}
	};
	if (fs.existsSync(root)) walk(root);
	return createHash('sha1').update(files.sort().join('\n')).digest('hex').slice(0, 12);
}

export default defineConfig({
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
		sveltekit(),
		absoluteAssetUrls()
	],
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
		/** See `coversVersion` above. */
		__COVERS_VERSION__: JSON.stringify(coversVersion())
	}
});
