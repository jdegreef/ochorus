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
 * #9879 (2026-11-24) overlapped 3 requests on Render, to fit the API's one
 * gunicorn worker with 4 threads. Back to 1 on 2026-11-25: with 3 in flight
 * the web deploys failed partway through the crawl (6, 17 and 18 minutes in)
 * while CI built the same commits fine against its own API, the pattern of
 * 2026-11-16..19 when the crawl knocked the 512 MB instance over. The faster
 * route is building against a local API (docs/build-without-prod-api.md),
 * not more pressure on production.
 *
 * An explicit PRERENDER_CONCURRENCY always wins: CI sets 8 against its own
 * API, and ochorus-web can set a higher value to try overlapping again.
 */

/** Pages in flight on Render when nothing says otherwise. */
export const RENDER_PRERENDER_CONCURRENCY = 1;

/** @param {Record<string, string | undefined>} env */
export function prerenderConcurrency(env) {
	const explicit = Number(env.PRERENDER_CONCURRENCY);
	if (Number.isInteger(explicit) && explicit > 0) return explicit;
	const onRender = Boolean((env.RENDER_GIT_COMMIT || '').trim());
	return onRender ? RENDER_PRERENDER_CONCURRENCY : 1;
}
