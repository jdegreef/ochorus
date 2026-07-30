import { locales } from '$lib/paraglide/runtime';
import { LIVE_LOCALES } from '$lib/live-locales.generated';

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
 * **No longer maintained by hand.** Which locales are advertised is a decision
 * recorded in the `Language` registry — an admin presses "Go live" — and
 * `scripts/fetch-live-locales.mjs` bakes that decision into
 * `live-locales.generated.ts` before every build. The reader is a prerendered
 * static site, so this has to be a build-time constant; that script is how a
 * database decision becomes one. If the API can't be reached the build FAILS,
 * rather than shipping a stale list that search engines would act on.
 *
 * So: being a UI locale means a reader can use the app in that language. Being
 * ADVERTISED means someone decided there is something in it worth ranking.
 */
export const ADVERTISED_LOCALES = LIVE_LOCALES;

export type AdvertisedLocale = (typeof ADVERTISED_LOCALES)[number];

/** UI locales deliberately kept out of the sitemap and hreflang, for messages. */
export const UNADVERTISED_LOCALES = (locales as readonly string[]).filter(
	(l) => !(ADVERTISED_LOCALES as readonly string[]).includes(l)
);

export const isAdvertised = (locale: string): boolean =>
	(ADVERTISED_LOCALES as readonly string[]).includes(locale);
