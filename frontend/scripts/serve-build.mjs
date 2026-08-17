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
 *   * `/x`       → build/x/index.html (redirect-free; the app canonicalises
 *                  to the trailing slash itself, and the host resolves both)
 *   * a real file → served with its content type
 *   * anything else → build/200.html with status 200 (the SPA fallback, which is
 *     why a missing page is a 200 carrying the app's own not-found UI)
 *
 * No dependencies on purpose: one fewer thing to keep pinned, and the routing
 * contract above is the thing under test, so it should be explicit here.
 */
import { createServer } from 'node:http';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { extname, join, normalize, resolve } from 'node:path';

const ROOT = resolve(process.argv[2] || 'build');
const PORT = Number(process.env.PORT || process.argv[3] || 4173);
const FALLBACK = join(ROOT, '200.html');

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
	if (await isFile(asIndex)) return asIndex;
	const asHtml = `${target}.html`;
	if (await isFile(asHtml)) return asHtml;
	return null;
}

createServer(async (req, res) => {
	const { pathname } = new URL(req.url, `http://localhost:${PORT}`);
	const file = (await resolveFile(pathname)) ?? FALLBACK;
	// Always 200 — including the fallback. That is what a static host does with
	// adapter-static's `fallback`, and it's why a missing page is a 200 carrying
	// the app's own not-found UI rather than an HTTP 404.
	res.writeHead(200, {
		'content-type': TYPES[extname(file)] ?? 'application/octet-stream',
		// Never cache in tests: a stale asset would make a fresh build look green.
		'cache-control': 'no-store'
	});
	createReadStream(file).pipe(res);
}).listen(PORT, () => {
	console.log(`serving ${ROOT} on http://localhost:${PORT} (SPA fallback: 200.html)`);
});
