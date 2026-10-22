/**
 * Whether this build is the native app's (iOS + Android, via Capacitor) rather
 * than the website's. scripts/build-app.mjs sets OCHORUS_TARGET=app; the one
 * definition, read by svelte.config.js (what to build) and vite.config.ts (the
 * `__APP__` constant behind `IS_APP`, and the app-only plugin). See MOBILE.md.
 */
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';

export const APP = process.env.OCHORUS_TARGET === 'app';

/**
 * The website origin the app loads its unbundled images from (`$lib/assetUrl`,
 * MOBILE.md "How the app loads images"): PUBLIC_SITE_URL as the app build sees
 * it — app-env/.env, then app-env/.env.local, a real environment variable
 * beating both, as SvelteKit reads that folder. ONE reading for both
 * consumers, so the URLs the bundle builds (vite.config.ts bakes this in as
 * `__APP_ASSET_ORIGIN__`) and the origin the app's CSP admits in img-src
 * (svelte.config.js) cannot disagree — if they did, every cover would be
 * blocked, silently. An app build without it fails here rather than shipping
 * an app with no pictures. Only called when APP is true.
 * @returns {string} an origin, e.g. `https://ochorus.com` (no trailing slash)
 */
export function appAssetOrigin() {
	const dir = fileURLToPath(new URL('./app-env', import.meta.url));
	const value = loadEnv('production', dir, 'PUBLIC_').PUBLIC_SITE_URL;
	try {
		if (value) return new URL(value).origin;
	} catch {
		// not a URL: fall through to the error below
	}
	throw new Error(
		'app build: PUBLIC_SITE_URL (app-env/.env) must be an absolute URL — the app ' +
			`loads its covers and portraits from it; got ${JSON.stringify(value ?? '')}`
	);
}
