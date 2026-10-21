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
import { basename, join, relative, sep } from 'node:path';

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
 * The `.woff` file names (basename) that are only a fallback: named by an
 * `@font-face` that also names a `.woff2`, and by no `@font-face` without one.
 * @param {string[]} cssTexts
 * @returns {Set<string>}
 */
export function fallbackWoffs(cssTexts) {
	const fallback = new Set();
	const needed = new Set();
	for (const css of cssTexts) {
		for (const [block] of css.matchAll(/@font-face\s*\{[^}]*\}/g)) {
			const woffs = [...block.matchAll(/url\(\s*["']?([^"')]+\.woff)["']?\s*\)/g)].map((m) =>
				basename(m[1])
			);
			const hasWoff2 = /\.woff2["')\s]/.test(block);
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
	const css = files.filter((f) => f.endsWith('.css')).map((f) => readFileSync(join(out, f), 'utf8'));
	const woffs = fallbackWoffs(css);
	const fonts = files.filter((f) => f.endsWith('.woff') && woffs.has(basename(f)));
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
