import type { Handle, HandleFetch } from '@sveltejs/kit';
import { building } from '$app/environment';
import { env as privateEnv } from '$env/dynamic/private';
import { localBuildApiOrigin, retarget, serviceKeyHeaders, withServiceKey } from '$lib/buildApi';
import { createBuildFetch } from '$lib/buildFetch';
import { markFallbackNoindex } from '$lib/fallbackShell';
import { markUnadvertisedNoindex } from '$lib/advertised-locales';
import { API_BASE_URL } from '$lib/config';
import { paraglideMiddleware } from '$lib/paraglide/server';
import { getTextDirection } from '$lib/paraglide/runtime';
import { markTabBar } from '$lib/presenceFlag';
import { loadUiCatalog } from '$lib/i18n.svelte';

// Runs during prerendering: sets the request-scoped locale (from the URL) and
// writes the correct <html lang="…" dir="…"> into each localized static page,
// flags <html data-tabbar> on a page that renders the phone tab bar, marks
// the 200.html fallback shell noindex ($lib/fallbackShell), and every
// page of a locale that isn't live yet ($lib/advertised-locales).
//
// `dir` has to be baked in here, not only set on hydration. The root layout does
// keep it in sync on client navigation, but this is a PRERENDERED site: without
// it, every Arabic page ships as `<html>` with no direction and paints
// left-to-right until JavaScript runs — and a crawler, or a reader on a slow
// connection, sees only that. Direction is part of the document, not a
// client-side enhancement.
export const handle: Handle = ({ event, resolve }) =>
	paraglideMiddleware(event.request, async ({ request, locale }) => {
		event.request = request;
		// `t()` reads this locale's UI strings while the page renders ($lib/i18n).
		await loadUiCatalog(locale);
		return resolve(event, {
			transformPageChunk: ({ html }) =>
				markUnadvertisedNoindex(
					markFallbackNoindex(
						// <html data-tabbar> where the page carries the phone tab bar,
						// so the first paint already keys on it ($lib/presenceFlag).
						markTabBar(
							html
								.replace('%paraglide.lang%', locale)
								.replace('%paraglide.dir%', getTextDirection(locale))
						),
						// The 200/404 shell answers every unbuilt path — see fallbackShell.
						event.url.pathname
					),
					// A locale not yet live is prerendered but kept out of the index.
					locale
				)
		});
	});

// Build-side CORS for the API calls load() makes with its own `fetch` (which is
// what inlines each response into the prerendered page — see `Fetch` in
// $lib/api.ts). SvelteKit replays browser CORS rules on those server-side
// fetches and throws unless the response carries an Access-Control-Allow-Origin
// matching the page's origin. The build's request carries no `Origin` header, so
// django-cors-headers (rightly) sends none back, and the prerender origin is not
// a real one to allow-list anyway. This hook runs only server-side — the
// prerender, and `vite dev` SSR; the deployed site is static, with no server —
// and the header is read only by SvelteKit's own server-side CORS check, so
// stamping it grants no browser anything: browsers do real CORS against the API.
const apiOrigin = API_BASE_URL ? new URL(API_BASE_URL).origin : null;

// At build time, API requests go through the build's fetch chain: chapters from
// batched runs, repeated lists from the first identical request ($lib/buildFetch).
const buildFetch = building && apiOrigin ? createBuildFetch(apiOrigin) : null;

// OCHORUS_BUILD_API=local (docs/build-without-prod-api.md): the build reads a
// throwaway API seeded from this checkout instead of crawling production. Only
// the network hop moves — `request.url`, the key SvelteKit inlines the response
// under, still names PUBLIC_API_BASE_URL, so hydration finds it. Null (and
// inert) unless the flag is set.
const localApi = building && apiOrigin ? localBuildApiOrigin(privateEnv) : null;

// The build is a server, so the API's guard (backend common/api_guard.py) can't
// recognise it by Origin: it sends OCHORUS_API_KEY instead, a private env var
// on ochorus-web. Only on the build's own network hop, after SvelteKit has
// recorded the load's request for inlining, so no page ever carries it.
const serviceKey = building && apiOrigin ? serviceKeyHeaders(privateEnv) : {};

// The build asks the API for UNCOMPRESSED bodies. The API gzips JSON for
// browsers (backend config/compression.py), and under the prerender's crawl
// Node's fetch (undici) crashed the whole build on gzip bodies with
// `assert(!this.paused)` in its parser — buildFetch keeps clones of responses
// it shares between identical requests, and a decoder stalled on an unread
// clone is what that assert trips on. A build on the API's own network gains
// nothing from compression anyway.
const identityEncoding = (input: RequestInfo | URL, init?: RequestInit): [Request, undefined] => {
	const req = new Request(input, init);
	const headers = new Headers(req.headers);
	headers.set('accept-encoding', 'identity');
	return [new Request(req, { headers }), undefined];
};

export const handleFetch: HandleFetch = async ({ event, request, fetch: kitFetch }) => {
	const fetch: typeof kitFetch = (input, init) => {
		const [keyed, keyedInit] = withServiceKey(input, init, apiOrigin ?? '', serviceKey);
		const target = localApi ? retarget(keyed, apiOrigin!, localApi) : keyed;
		if (!building || !apiOrigin) return kitFetch(target, keyedInit);
		return kitFetch(...identityEncoding(target, keyedInit));
	};
	const response = buildFetch ? await buildFetch(request, fetch) : await fetch(request);
	if (!apiOrigin || new URL(request.url).origin !== apiOrigin) return response;
	const headers = new Headers(response.headers);
	headers.set('access-control-allow-origin', event.url.origin);
	return new Response(response.body, {
		status: response.status,
		statusText: response.statusText,
		headers
	});
};
