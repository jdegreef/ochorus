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
 *   * Website-only output is removed: og/ holds the share-card images link
 *     previews fetch from ochorus.com, never shown in the app (~40 MB).
 */

import { execFileSync } from 'node:child_process';
import { existsSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'build-app');

/** Website-only folders under static/ that the app bundle leaves out. */
const WEB_ONLY = ['og'];

const run = (cmd, args, env = {}) =>
	execFileSync(cmd, args, { cwd: ROOT, stdio: 'inherit', env: { ...process.env, ...env } });

rmSync(OUT, { recursive: true, force: true });
run('npx', ['vite', 'build'], { OCHORUS_TARGET: 'app' });

if (!existsSync(join(OUT, 'index.html'))) {
	console.error('\n✗ app build: build-app/index.html is missing — the app would open blank.\n');
	process.exit(1);
}
for (const dir of WEB_ONLY) rmSync(join(OUT, dir), { recursive: true, force: true });

if (!process.argv.includes('--no-sync')) run('npx', ['cap', 'sync']);
