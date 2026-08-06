import { isAdvertised } from './advertised-locales';

/**
 * Which locales the footer language strip lists.
 *
 * The base rule is `isAdvertised`: the strip is a promise ("Ochorus is
 * available in your language"), and a locale with nothing to read delivers a
 * fully translated interface wrapped around an empty library. Same rule the
 * sitemap and hreflang use, so the site makes one consistent claim.
 *
 * The exception is the locale the reader is ACTUALLY IN. Filtering on
 * `isAdvertised` alone meant that on an unadvertised-but-wired locale (/hi
 * today, /ar until it filled up) the strip named five other languages and not
 * the reader's own — no "you are here" marker anywhere, because the current
 * locale had been filtered out before the strip could mark it. Withholding the
 * advertisement is the point; withholding the reader's own position in the list
 * is just a broken control.
 *
 * Lives here rather than inline in the layout so it can be asserted: the two
 * locale lists this sits between (compiled UI locales, and the registry's live
 * set) are maintained independently and have disagreed in both directions.
 */
export function footerLocales<T extends { code: string }>(available: T[], current: string): T[] {
	return available.filter((l) => isAdvertised(l.code) || l.code === current);
}
