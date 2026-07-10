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
	]
});
