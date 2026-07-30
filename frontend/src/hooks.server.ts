import type { Handle } from '@sveltejs/kit';
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
