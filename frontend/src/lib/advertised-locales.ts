import { locales } from '$lib/paraglide/runtime';

/**
 * The locales whose pages we ADVERTISE to search engines — in `sitemap.xml` and
 * in `hreflang` alternates. This is deliberately NOT the same as the UI locale
 * list.
 *
 * A locale can be fully wired in the interface and still have nothing to read.
 * Portuguese was exactly that when it landed: 0 books, 0 plans, 0 topics, 1
 * sermon — author bios fall back to English. Arabic followed days later with
 * zero of everything. Two in one week is why this is a list and not a
 * one-off exclusion. Advertising it publishes English
 * prose at a Portuguese URL while `hreflang="pt"` asserts that page IS the
 * Portuguese version. That is thin/duplicate content, and it is worse than the
 * empty shell it would replace: a shell gets ignored, a thin page gets indexed
 * and counted against the site.
 *
 * So: being a UI locale means a reader can use the app in that language. Being
 * ADVERTISED means there is something in it worth ranking. Add a locale here
 * once it has works — `sitemap.xml` asserts this list against the real
 * per-locale counts, so a locale that gains (or loses) content fails the build
 * rather than drifting silently.
 */
export const ADVERTISED_LOCALES = ['en', 'es', 'sw', 'lg', 'pt'] as const;

export type AdvertisedLocale = (typeof ADVERTISED_LOCALES)[number];

/** UI locales deliberately kept out of the sitemap and hreflang, for messages. */
export const UNADVERTISED_LOCALES = (locales as readonly string[]).filter(
	(l) => !(ADVERTISED_LOCALES as readonly string[]).includes(l)
);

export const isAdvertised = (locale: string): boolean =>
	(ADVERTISED_LOCALES as readonly string[]).includes(locale);
