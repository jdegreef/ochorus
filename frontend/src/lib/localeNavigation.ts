import { baseLocale, locales } from '$lib/paraglide/runtime';

/**
 * Does a navigation from `from` to `to` change the UI locale?
 *
 * The locale lives in the URL prefix and is read ONCE per document: Paraglide's
 * messages, `<html lang>` and `<html dir>` are not reactive to it. So a
 * client-side hop from `/ar/...` to `/books/...` kept the Arabic document's
 * `dir="rtl"` and half its chrome — the QA report's "RTL formatting remains
 * after switching back to English" and some of its mixed-language pages. A
 * handful of links opted out with `data-sveltekit-reload`, but every
 * `editionHref` (shelf, resume, notebook) and any future cross-locale link
 * leaked. The root layout asks this on every navigation and turns a crossing
 * into a full load instead.
 *
 * Another origin is never a crossing: the browser leaves the app either way.
 */
export function crossesLocale(from: URL | undefined, to: URL | undefined): boolean {
	if (!from || !to || from.origin !== to.origin) return false;
	return localeOf(from) !== localeOf(to);
}

/**
 * The locale a URL routes to: its first path segment when that is a locale,
 * else the (unprefixed) base locale — the `url` strategy's default patterns.
 * Parsed here rather than via `getLocaleForUrl`, whose answer also depends on
 * the compiled strategy list (cookie first, in the CLI-compiled runtime the
 * unit tests load), not just the URL.
 */
function localeOf(url: URL): string {
	const first = url.pathname.split('/')[1] ?? '';
	return (locales as readonly string[]).includes(first) ? first : baseLocale;
}
