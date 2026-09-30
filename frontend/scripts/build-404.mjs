#!/usr/bin/env node
/**
 * Write build/404.html — the SPA shell the static host serves, with a 404
 * status, for any path that has no prerendered file and no render.yaml rule.
 *
 * adapter-static emits one fallback (`200.html`), and render.yaml now rewrites
 * only the client-only app routes to it ($lib/shellRoutes). Everything else
 * that misses — a typo'd slug, a dead WordPress URL, an untranslated
 * `/es/books/<en-only>/` — gets Render's `/404.html`. It is a byte copy of the
 * 200 shell (already `noindex`, see $lib/fallbackShell), so the router boots
 * and renders the app's own not-found page exactly as before; only the status
 * changes, which is what stops Google counting them as soft 404s.
 */
import { copyFileSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';

const BUILD = resolve(process.argv[2] || 'build');
const shell = join(BUILD, '200.html');
if (!existsSync(shell)) {
	console.error(`build-404: ${shell} is missing — did adapter-static's fallback change?`);
	process.exit(1);
}
copyFileSync(shell, join(BUILD, '404.html'));
console.log('build-404: wrote build/404.html from the 200.html shell');
