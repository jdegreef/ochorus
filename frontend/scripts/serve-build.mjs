#!/usr/bin/env node
/**
 * Serve `build/` the way the static host does — for the Playwright smoke suite.
 *
 * `vite preview` is NOT usable for this: it serves SvelteKit's own output and
 * SSRs anything not prerendered, so `build/200.html` is never served and a
 * request for a missing page renders through a server path production doesn't
 * have. Testing against it would prove the app works in a mode we never deploy.
 *
 * This mirrors adapter-static on Render instead:
 *   * `/x/`      → build/x/index.html
 *   * `/x`       → build/x.html (render.yaml's index-page rewrites, which match
 *                  either slash form) — but NOT build/x/index.html: Render
 *                  doesn't resolve a no-slash URL to a directory index, so
 *                  production answers that with the 404 shell until the edge
 *                  301 (docs/seo-edge-rules.md) catches it first
 *   * a real file → served with its content type
 *   * a client-only app route ($lib/shellRoutes, every locale) → build/200.html
 *     with status 200 — render.yaml's bare and `/:lang` rewrites
 *   * anything else → build/404.html with status 404 (Render's not-found page:
 *     the same SPA shell, so the app still renders its own not-found UI, but
 *     the status is honest — see scripts/build-404.mjs)
 *
 * No dependencies on purpose: one fewer thing to keep pinned, and the routing
 * contract above is the thing under test, so it should be explicit here.
 */
import { createServer } from 'node:http';
import { createReadStream, readFileSync } from 'node:fs';
import { stat } from 'node:fs/promises';
import { extname, join, normalize, resolve } from 'node:path';
import { isShellPath } from '../src/lib/shellRoutes.ts';

const ROOT = resolve(process.argv[2] || 'build');
const PORT = Number(process.env.PORT || process.argv[3] || 4173);
const SHELL = join(ROOT, '200.html');
const NOT_FOUND = join(ROOT, '404.html');
const LOCALES = JSON.parse(
	readFileSync(new URL('../project.inlang/settings.json', import.meta.url), 'utf8')
).locales;

/** The path with any UI-locale prefix removed, as render.yaml's `/:lang` rules match. */
const unprefixed = (pathname) => {
	const [, first, rest] = /^\/([^/]+)(.*)$/.exec(pathname) ?? [];
	return first && LOCALES.includes(first) && first !== 'en' ? rest || '/' : pathname;
};

const TYPES = {
	'.html': 'text/html; charset=utf-8',
	'.js': 'text/javascript; charset=utf-8',
	'.mjs': 'text/javascript; charset=utf-8',
	'.css': 'text/css; charset=utf-8',
	'.json': 'application/json; charset=utf-8',
	'.xml': 'application/xml; charset=utf-8',
	'.txt': 'text/plain; charset=utf-8',
	'.svg': 'image/svg+xml',
	'.png': 'image/png',
	'.jpg': 'image/jpeg',
	'.jpeg': 'image/jpeg',
	'.webp': 'image/webp',
	'.avif': 'image/avif',
	'.ico': 'image/x-icon',
	'.woff': 'font/woff',
	'.woff2': 'font/woff2',
	'.webmanifest': 'application/manifest+json'
};

const isFile = async (p) => {
	try {
		return (await stat(p)).isFile();
	} catch {
		return false;
	}
};

/** Resolve a URL pathname to a file inside ROOT, or null to use the fallback. */
async function resolveFile(pathname) {
	// Block traversal: normalise, then require the result stay under ROOT.
	const target = resolve(join(ROOT, normalize(decodeURIComponent(pathname))));
	if (target !== ROOT && !target.startsWith(ROOT + '/')) return null;

	if (await isFile(target)) return target;
	const asIndex = join(target, 'index.html');
	if (pathname.endsWith('/') && (await isFile(asIndex))) return asIndex;
	const asHtml = `${target}.html`;
	if (await isFile(asHtml)) return asHtml;
	return null;
}

createServer(async (req, res) => {
	const { pathname } = new URL(req.url, `http://localhost:${PORT}`);
	const found = await resolveFile(pathname);
	const shell = !found && isShellPath(unprefixed(pathname));
	const file = found ?? (shell ? SHELL : NOT_FOUND);
	res.writeHead(found || shell ? 200 : 404, {
		'content-type': TYPES[extname(file)] ?? 'application/octet-stream',
		// Never cache in tests: a stale asset would make a fresh build look green.
		'cache-control': 'no-store'
	});
	createReadStream(file).pipe(res);
}).listen(PORT, () => {
	console.log(`serving ${ROOT} on http://localhost:${PORT} (app routes: 200.html, else 404.html)`);
});
