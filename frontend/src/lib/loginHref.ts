import { deLocalizeHref } from '$lib/paraglide/runtime';

/**
 * Where the header's "Sign in" link should point, given the page the reader is
 * on — carrying that page along so sign-in returns them to it.
 *
 * Pure and tested because the guard below is easy to get wrong in a way that is
 * invisible in English. It shipped comparing the RAW pathname against
 * '/login': on every other locale the pathname carries its prefix (`/es/login`,
 * `/pt/login`), so the guard never matched, the link became
 * `?redirect=/es/login`, and a successful sign-in redirected the reader
 * straight back to the login page. It read as an authentication failure, and it
 * hit every locale except the one anyone would test in.
 *
 * The result is a NON-localized path — the caller localizes it — while
 * `redirect` is the localized path the reader is actually on, which is why the
 * login page can consume it without re-localizing.
 */
export function loginHref(pathname: string, search = ''): string {
	// De-localized purely to judge the shape; the redirect keeps its prefix.
	if (deLocalizeHref(pathname).startsWith('/login')) return '/login';
	// `search` too: returning from sign-in to `/search` without its `?q=` threw
	// away the query the reader came from.
	return `/login?redirect=${encodeURIComponent(pathname + search)}`;
}

/** Open the login page on its "create account" form. */
export const withSignup = (href: string): string =>
	`${href}${href.includes('?') ? '&' : '?'}mode=signup`;
