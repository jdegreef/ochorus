import type { IconName } from '$lib/components/Icon.svelte';
import { ORIGINALS_PATH } from '$lib/originals';

/**
 * The one ordered source for the reader-facing content-type lists.
 *
 * The top nav, the footer's Explore group and the command palette each listed
 * these destinations in their own hand-written order, and the three drifted (a
 * new hub reached one surface and not the others, in a different position). They
 * now all `.map` these two arrays, so their order cannot come apart: change the
 * order here and every surface moves together.
 *
 * The sitemap is deliberately NOT derived from this. Its section order answers a
 * different question — crawl budget and per-locale coverage, with topics/plans
 * folded into the small `pages` tail — not "what order does a reader meet these
 * in". See `sitemap.ts`.
 */

/** A primary content destination: earns a top-nav slot and a footer link. */
export interface NavDest {
	/** Canonical path, no trailing slash. Each surface applies its own
	 *  `localizeHref` / trailing-slash treatment. */
	href: string;
	/** i18n key for the label (dotted; resolved with `t()` per surface). */
	labelKey: string;
	/** The top-nav icon. */
	icon: IconName;
}

/** An English-only hub: the footer Explore group and the palette, gated to
 *  English, and never the top nav (an entry point for search, not a primary
 *  journey). English-only because the content is lifted from / parsed against
 *  the English works, so there is no localized page to send anyone to. */
export interface HubDest {
	href: string;
	labelKey: string;
}

/** Books · Topics · Plans · Sermons · Biographies — the primary journeys. */
export const PRIMARY_NAV: NavDest[] = [
	{ href: '/books', labelKey: 'nav.books', icon: 'book' },
	{ href: '/topics', labelKey: 'nav.topics', icon: 'tag' },
	{ href: '/plans', labelKey: 'nav.plans', icon: 'calendar' },
	{ href: '/sermons', labelKey: 'nav.sermons', icon: 'mic' },
	{ href: '/biographies', labelKey: 'nav.biographies', icon: 'users' }
];

/** Articles · Scripture · Quotes — English-only hubs (footer + palette). */
export const ENGLISH_HUBS: HubDest[] = [
	{ href: '/articles', labelKey: 'nav.articles' },
	{ href: '/scripture', labelKey: 'reader.scripture' },
	{ href: '/quotes', labelKey: 'nav.quotes' }
];

/** Ochorus Originals — the house imprint's shelf. Not an English-only hub: its
 *  books are translated, so the footer and the palette offer it in every
 *  locale (the page lists only that language's books). Sits after the hubs, so
 *  English readers meet Articles · Scripture · Quotes · Originals · RSS. */
export const ORIGINALS_DEST: HubDest = { href: ORIGINALS_PATH, labelKey: 'nav.originals' };
