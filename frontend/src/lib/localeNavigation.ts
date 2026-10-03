import { extractLocaleFromUrl } from '$lib/paraglide/runtime';

/**
 * Does a navigation from `from` to `to` change the UI locale? The locale (the
 * URL prefix) is read once per document — messages and `<html lang/dir>` don't
 * follow it — so the root layout turns such a navigation into a full load.
 */
export function crossesLocale(from: URL | undefined, to: URL | undefined): boolean {
	if (!from || !to || from.origin !== to.origin) return false;
	return extractLocaleFromUrl(from.href) !== extractLocaleFromUrl(to.href);
}
