/**
 * What scripts/build-app.mjs trims from build-app/ after Vite, and the size
 * gate that keeps it trimmed. Pure helpers over a directory, so
 * `src/lib/appBundle.test.ts` can run them on a temp folder.
 *
 * Three things a phone does not need in its bundle:
 *
 *   * the static folders the app loads from the website (app-assets.js
 *     REMOTE_DIRS — covers, portraits, illustrations, share cards, PDFs), less
 *     the few files it `fetch`es (KEEP_LOCAL);
 *   * the website's service worker (the app never registers one — $lib/pwa);
 *   * the legacy `.woff` fallback of every webfont that also ships a `.woff2`.
 *     Every web view the app runs in (WKWebView, Android System WebView)
 *     takes woff2, and a browser stops at the first `src` it supports, so the
 *     fallback is never fetched there. A `.woff` named by an `@font-face`
 *     WITHOUT a woff2 beside it is kept: that one is the only copy.
 */

import { existsSync, readdirSync, readFileSync, rmSync, statSync } from 'node:fs';
import { join, posix, relative, sep } from 'node:path';

/**
 * Every file under `dir`, as paths relative to it with forward slashes.
 * @param {string} dir
 * @returns {string[]}
 */
export function listFiles(dir) {
	/** @type {string[]} */
	const out = [];
	const walk = (/** @type {string} */ d) => {
		for (const entry of readdirSync(d, { withFileTypes: true })) {
			const full = join(d, entry.name);
			if (entry.isDirectory()) walk(full);
			else out.push(relative(dir, full).split(sep).join('/'));
		}
	};
	if (existsSync(dir)) walk(dir);
	return out;
}

/** Total bytes of every file under `dir`. @param {string} dir */
export function dirBytes(dir) {
	return listFiles(dir).reduce((sum, f) => sum + statSync(join(dir, f)).size, 0);
}

/**
 * Where a CSS `url()` points, as a path relative to the build root: a
 * root-relative URL from the root, anything else from the stylesheet's own
 * folder. Null for one that leaves the build (`https:`, `data:`, `//host`).
 * @param {string} url
 * @param {string} cssFile the stylesheet, relative to the build root
 * @returns {string | null}
 */
export function resolveCssUrl(url, cssFile) {
	const path = url.replace(/[?#].*$/, '');
	if (/^[a-z][a-z0-9+.-]*:/i.test(path) || path.startsWith('//')) return null;
	const resolved = path.startsWith('/')
		? posix.normalize(path.slice(1))
		: posix.join(posix.dirname(cssFile), path);
	return resolved.startsWith('../') ? null : resolved;
}

/**
 * The `.woff` files (paths relative to the build root) that are only a
 * fallback: named by an `@font-face` that also names a `.woff2`, and by no
 * `@font-face` without one. Matched by resolved path, never by file name, so
 * a same-named file elsewhere in the build is never caught up in it.
 * @param {{ file: string, css: string }[]} sheets each stylesheet, relative to the build root
 * @returns {Set<string>}
 */
export function fallbackWoffs(sheets) {
	const fallback = new Set();
	const needed = new Set();
	for (const { file, css } of sheets) {
		for (const [block] of css.matchAll(/@font-face\s*\{[^}]*\}/g)) {
			const woffs = [...block.matchAll(/url\(\s*["']?([^"')]+\.woff(?:[?#][^"')]*)?)["']?\s*\)/g)]
				.map((m) => resolveCssUrl(m[1], file))
				.filter((p) => p !== null);
			const hasWoff2 = /\.woff2[?#"')\s]/.test(block);
			for (const w of woffs) (hasWoff2 ? fallback : needed).add(w);
		}
	}
	for (const w of needed) fallback.delete(w);
	return fallback;
}

/**
 * The files to delete from an app build: relative paths under `out`.
 * @param {string} out
 * @param {{ remoteDirs: string[], keepLocal: string[] }} assets
 * @returns {string[]}
 */
export function prunable(out, { remoteDirs, keepLocal }) {
	const files = listFiles(out);
	const keep = new Set(keepLocal);
	const remote = files.filter((f) => remoteDirs.includes(f.split('/')[0]) && !keep.has(f));
	const sheets = files
		.filter((f) => f.endsWith('.css'))
		.map((file) => ({ file, css: readFileSync(join(out, file), 'utf8') }));
	const woffs = fallbackWoffs(sheets);
	const fonts = files.filter((f) => woffs.has(f));
	const worker = files.filter((f) => f === 'service-worker.js');
	return [...remote, ...fonts, ...worker];
}

/**
 * Delete `prunable` files, then any folder left empty. Returns bytes freed.
 * @param {string} out
 * @param {{ remoteDirs: string[], keepLocal: string[] }} assets
 */
export function prune(out, assets) {
	let freed = 0;
	for (const f of prunable(out, assets)) {
		const full = join(out, f);
		freed += statSync(full).size;
		rmSync(full);
	}
	for (const dir of assets.remoteDirs) removeEmptyDirs(join(out, dir));
	return freed;
}

/** Remove `dir` and its subfolders bottom-up wherever they hold no files. @param {string} dir */
function removeEmptyDirs(dir) {
	if (!existsSync(dir) || !statSync(dir).isDirectory()) return;
	for (const entry of readdirSync(dir)) removeEmptyDirs(join(dir, entry));
	if (!readdirSync(dir).length) rmSync(dir, { recursive: true });
}

/** Megabytes, one decimal. @param {number} bytes */
export const mb = (bytes) => `${(bytes / 1024 / 1024).toFixed(1)} MB`;
