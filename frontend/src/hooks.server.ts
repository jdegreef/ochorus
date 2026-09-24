import type { Handle, HandleFetch } from '@sveltejs/kit';
import { API_BASE_URL } from '$lib/config';
import { paraglideMiddleware } from '$lib/paraglide/server';
import { getTextDirection } from '$lib/paraglide/runtime';

// Runs during prerendering: sets the request-scoped locale (from the URL) and
// writes the correct <html lang="…" dir="…"> into each localized static page.
//
// `dir` has to be baked in here, not only set on hydration. The root layout does
// keep it in sync on client navigation, but this is a PRERENDERED site: without
// it, every Arabic page ships as `<html>` with no direction and paints
// left-to-right until JavaScript runs — and a crawler, or a reader on a slow
// connection, sees only that. Direction is part of the document, not a
// client-side enhancement.
export const handle: Handle = ({ event, resolve }) =>
	paraglideMiddleware(event.request, ({ request, locale }) => {
		event.request = request;
		return resolve(event, {
			transformPageChunk: ({ html }) =>
				html
					.replace('%paraglide.lang%', locale)
					.replace('%paraglide.dir%', getTextDirection(locale))
		});
	});

// Build-side CORS for the API calls load() makes with its own `fetch` (which is
// what inlines each response into the prerendered page — see `Fetch` in
// $lib/api.ts). SvelteKit replays browser CORS rules on those server-side
// fetches and throws unless the response carries an Access-Control-Allow-Origin
// matching the page's origin. The build's request carries no `Origin` header, so
// django-cors-headers (rightly) sends none back, and the prerender origin is not
// a real one to allow-list anyway. This hook only ever runs at build time — the
// site is static, there is no server — so stamping the header here grants no
// browser anything: at runtime the browser does real CORS against the API.
const apiOrigin = API_BASE_URL ? new URL(API_BASE_URL).origin : null;

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
	const response = await fetch(request);
	if (!apiOrigin || new URL(request.url).origin !== apiOrigin) return response;
	const headers = new Headers(response.headers);
	headers.set('access-control-allow-origin', event.url.origin);
	return new Response(response.body, {
		status: response.status,
		statusText: response.statusText,
		headers
	});
};
