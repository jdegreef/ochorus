/**
 * Where a static image is fetched from: the ONE place that knows the native app
 * does not bundle `static/covers/`, `portraits/`, `illustrations/`, … and loads
 * them from the website instead (MOBILE.md, "How the app loads images").
 *
 * On the website every function here returns its input unchanged — `IS_APP` is
 * a build-time constant, so the web bundle carries none of the rewriting. In
 * the app, a root-relative path under one of `REMOTE_DIRS` (app-assets.js, the
 * same list scripts/build-app.mjs deletes from the bundle) is prefixed with the
 * site's origin (`PUBLIC_SITE_URL`, app-env/.env). Anything else — an icon, a
 * mark, an emblem, an already-absolute URL, `data:`/`blob:` — is left alone.
 *
 * Apply it where an `<img>`'s `src`/`srcset` is built, never inside the pure
 * helpers (`coverArt`, `portraits`) that also feed scripts, the share cards and
 * the offline cache, which all want the site path.
 */
import { IS_APP } from '$lib/platform';
import { SITE_URL } from '$lib/config';
import { KEEP_LOCAL, REMOTE_DIRS } from '../../app-assets.js';

/** `path` against `origin` when the app does not bundle it; else `path`. Pure,
 *  so the rule is testable without an app build. (No module-level tables: the
 *  website's bundle drops this function whole, and a top-level `new RegExp`
 *  would stay behind as a side effect.) */
export function remoteAsset(path: string, origin: string): string {
	const [lead, dir, ...rest] = path.split('/');
	if (lead !== '' || !rest.length || !REMOTE_DIRS.includes(dir)) return path;
	if (KEEP_LOCAL.includes(path.slice(1).replace(/[?#].*$/, ''))) return path;
	return origin.replace(/\/+$/, '') + path;
}

/** A `srcset`'s every candidate through `remoteAsset`, descriptors kept. */
export function remoteSrcset(srcset: string, origin: string): string {
	return srcset
		.split(',')
		.map((candidate) => {
			const [url, ...descriptors] = candidate.trim().split(/\s+/);
			return [remoteAsset(url, origin), ...descriptors].join(' ');
		})
		.join(', ');
}

/** Server-sanitized body HTML with its `<img src>`s (in-chapter illustrations)
 *  through `remoteAsset`. The sanitizer admits only `src="/illustrations/…"`
 *  (library/sanitize.py), so a pattern finds every one. */
export function remoteHtml(html: string, origin: string): string {
	return html.replace(/(<img\b[^>]*?\ssrc=")([^"]+)"/gi, (_, head, src) => `${head}${remoteAsset(src, origin)}"`);
}

/** An image path as this build should fetch it (see the header). */
export function assetUrl<T extends string | null | undefined>(path: T): T {
	return (IS_APP && path ? remoteAsset(path, SITE_URL) : path) as T;
}

/** A `srcset` as this build should fetch it. */
export function assetSrcset<T extends string | null | undefined>(srcset: T): T {
	return (IS_APP && srcset ? remoteSrcset(srcset, SITE_URL) : srcset) as T;
}

/** Body HTML whose images this build should fetch from where `assetUrl` says. */
export function assetHtml(html: string): string {
	return IS_APP && html ? remoteHtml(html, SITE_URL) : html;
}
