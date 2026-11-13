/**
 * "Listen" from a link (design review 2026-11, #24): the home page's sermon
 * rows link to `/sermons/<slug>?listen`, and the sermon page starts reading
 * aloud once it is ready — the same as pressing its own Listen button.
 *
 * Browsers only let a page speak after the reader has interacted with it.
 * Following the link inside the app keeps that permission (the same
 * document), so the sermon starts; opened fresh in a new tab it may not, and
 * the page simply waits for its Listen button, as it always has.
 */
export const LISTEN_PARAM = 'listen';

/** Whether this URL asks for Listen to start on arrival. */
export const wantsListen = (url: URL): boolean => url.searchParams.has(LISTEN_PARAM);

/** The same URL without the request, so a reload or a shared link doesn't
 *  start speaking again. */
export function withoutListen(url: URL): URL {
	const next = new URL(url);
	next.searchParams.delete(LISTEN_PARAM);
	return next;
}
