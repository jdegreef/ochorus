/**
 * How many pages the web build prerenders at once (svelte.config.js).
 *
 * The production build crawls the LIVE API, one page after another by default.
 * Each page's render takes a few milliseconds; the rest is the round trip to
 * api.ochorus.com. With ~45,000 chapter pages across the live languages that
 * serial wait is most of the build: it took ~21 minutes before the Bibles and
 * the Japanese and Russian shelves landed, and over an hour after. CI renders
 * the same site 8 at a time against a local API in about 11 minutes.
 *
 * So on Render the build overlaps its requests, but only 3 at a time. The API
 * runs one gunicorn worker with 4 threads (backend/Dockerfile): 3 keeps the
 * crawl inside that worker's threads, with one left for readers, and still
 * leaves the crawl's memory well under the 512 MB plan (the worry that kept
 * this at 1 after 2026-09-26, fixed since by the single-worker, threaded
 * layout and MALLOC_ARENA_MAX). Chapters come in batches of 25
 * ($lib/chapterBatch), so most pages make no API request of their own.
 *
 * An explicit PRERENDER_CONCURRENCY always wins: CI sets 8 against its own
 * API, and setting 1 on Render is the rollback if the API ever struggles.
 * Anywhere else (a local `npm run build` against production) stays at 1.
 */

/** Pages in flight on Render when nothing says otherwise. */
export const RENDER_PRERENDER_CONCURRENCY = 3;

/** @param {Record<string, string | undefined>} env */
export function prerenderConcurrency(env) {
	const explicit = Number(env.PRERENDER_CONCURRENCY);
	if (Number.isInteger(explicit) && explicit > 0) return explicit;
	const onRender = Boolean((env.RENDER_GIT_COMMIT || '').trim());
	return onRender ? RENDER_PRERENDER_CONCURRENCY : 1;
}
