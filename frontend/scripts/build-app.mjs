/**
 * Build the reader for the native app (iOS + Android, via Capacitor) into
 * build-app/, then copy it into the native projects.
 *
 *   npm run app:build          # web bundle + `cap sync` (what you run on the Mac)
 *   npm run app:build -- --no-sync   # web bundle only (CI, or no native toolchain)
 *
 * What differs from the website's `npm run build` (see frontend/MOBILE.md):
 *
 *   * OCHORUS_TARGET=app — svelte.config.js prerenders nothing and emits one
 *     index.html shell; `IS_APP` ($lib/platform) turns off what an app can't
 *     use yet (the service worker, cache-based offline downloads, sign-in).
 *   * Settings come from app-env/ only (see app-env/.env), never from the
 *     website's frontend/.env. Real environment variables still win.
 *   * No prebuild: the app build reads the committed live-locales list instead
 *     of asking the API, and waits for no API release — it prerenders nothing,
 *     so it needs no network at all.
 *   * A lighter bundle (scripts/app-bundle.mjs): the static folders listed in
 *     app-assets.js — covers, portraits, illustrations, share cards, PDFs,
 *     ~250 MB — are left out, and `$lib/assetUrl` loads them from the website
 *     (PUBLIC_SITE_URL) instead. So are the website's service worker and the
 *     legacy .woff twin of every font that also ships a .woff2.
 *   * Size gate: the finished build-app/ must fit `appBundle.raw` in
 *     bundle-budget.json, or the build fails (CI runs this on every frontend PR).
 */

import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { KEEP_LOCAL, REMOTE_DIRS } from '../app-assets.js';
import { dirBytes, mb, prune } from './app-bundle.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'build-app');

const run = (cmd, args, env = {}) =>
	execFileSync(cmd, args, { cwd: ROOT, stdio: 'inherit', env: { ...process.env, ...env } });

rmSync(OUT, { recursive: true, force: true });
run('npx', ['vite', 'build'], { OCHORUS_TARGET: 'app' });

if (!existsSync(join(OUT, 'index.html'))) {
	console.error('\n✗ app build: build-app/index.html is missing — the app would open blank.\n');
	process.exit(1);
}

const freed = prune(OUT, { remoteDirs: REMOTE_DIRS, keepLocal: KEEP_LOCAL });
const total = dirBytes(OUT);
const { appBundle } = JSON.parse(readFileSync(join(ROOT, 'bundle-budget.json'), 'utf8'));
console.log(`\napp bundle: ${mb(total)} (budget ${mb(appBundle.raw)}; ${mb(freed)} left to the website)`);
if (total > appBundle.raw) {
	console.error(
		`\n✗ app build: build-app/ is ${mb(total)}, over its ${mb(appBundle.raw)} budget ` +
			`(bundle-budget.json "appBundle"). Something big was bundled that the app could load ` +
			`from the website (add its folder to app-assets.js REMOTE_DIRS), or raise the budget ` +
			`deliberately and say why in the PR.\n`
	);
	process.exit(1);
}

if (!process.argv.includes('--no-sync')) run('npx', ['cap', 'sync']);
