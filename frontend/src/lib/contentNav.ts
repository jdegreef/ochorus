import type { IconName } from '$lib/components/Icon.svelte';
import { ORIGINALS_PATH } from '$lib/originals';
import { AUDIENCE_HUBS } from '$lib/audienceHub';

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
	/** Its library-palette role: the nav wears `--section-<section>` on the
	 *  icon and the active pill (app.css, "THE LIBRARY PALETTE"). */
	section: NavSection;
	/** The printer's ornament under its page title (`<Fleuron>`), drawn from
	 *  `/marks/ornament-<name>.svg`; its emblem beside that title is
	 *  `/marks/emblem-<section>.svg` (marks.test.ts checks both exist). */
	ornament: Ornament;
}

export type NavSection = 'books' | 'topics' | 'plans' | 'sermons' | 'biographies';

/** A section's ornament, in gold like every ornament (STYLE_GUIDE §1): a lamp
 *  for Books ("Thy word is a lamp", Ps 119:105), an anchor for Topics (hope,
 *  Heb 6:19), a vine for Plans (abiding, day by day, John 15), a descending
 *  dove for Sermons, a laurel for Biographies. 'leaf' is the house ornament,
 *  for every page that is not a section's. */
export type Ornament = 'leaf' | 'lamp' | 'anchor' | 'vine' | 'dove' | 'laurel';

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
	{ href: '/books', labelKey: 'nav.books', icon: 'book', section: 'books', ornament: 'lamp' },
	{ href: '/topics', labelKey: 'nav.topics', icon: 'tag', section: 'topics', ornament: 'anchor' },
	{ href: '/plans', labelKey: 'nav.plans', icon: 'calendar', section: 'plans', ornament: 'vine' },
	{ href: '/sermons', labelKey: 'nav.sermons', icon: 'mic', section: 'sermons', ornament: 'dove' },
	{ href: '/biographies', labelKey: 'nav.biographies', icon: 'users', section: 'biographies', ornament: 'laurel' }
];

/** A section's entry in PRIMARY_NAV — its icon, ornament and the rest. */
export const sectionDest = (section: NavSection): NavDest => PRIMARY_NAV.find((d) => d.section === section)!;

/** Articles · Scripture · Quotes — English-only hubs (footer + palette). */
export const ENGLISH_HUBS: HubDest[] = [
	{ href: '/articles', labelKey: 'nav.articles' },
	{ href: '/scripture', labelKey: 'reader.scripture' },
	{ href: '/quotes', labelKey: 'nav.quotes' }
];

/** Book Series — every series in this language, hanging off Books. Not a top-nav
 *  slot (the Books page's rail and count link are its way in there), but every
 *  locale's footer Explore group and the palette offer it right after the
 *  primary five: a series is translated content, so each locale has its own
 *  index. The trailing slash is added by `localizeHref` ($lib/canonicalRedirect isSlashedPath). */
export const SERIES_DEST: HubDest = { href: '/series', labelKey: 'nav.series' };

/** Ochorus Originals — the house imprint's shelf. Not an English-only hub: its
 *  books are translated, so the footer and the palette offer it in every
 *  locale (the page lists only that language's books). Sits after the hubs, so
 *  English readers meet Articles · Scripture · Quotes · Originals · RSS. */
export const ORIGINALS_DEST: HubDest = { href: ORIGINALS_PATH, labelKey: 'nav.originals' };

/** Authors & Books A–Z — the one page linking every writer and every book in
 *  a language ($lib/authorIndex), so the whole library is two clicks from any
 *  page. Every locale's footer Explore group and the palette offer it after
 *  Book Series. The trailing slash comes from `localizeHref` (isSlashedPath). */
export const AZ_INDEX_DEST: HubDest = { href: '/authors', labelKey: 'nav.azIndex' };

/** The young-reader hubs — /young-readers/ and /teens/ ($lib/audienceHub).
 *  Like Book Series, not a top-nav slot: every locale's footer Explore group,
 *  the palette and the phone's More sheet offer them right after Book Series
 *  (their books are translated, so each locale has its own copy). The trailing
 *  slash comes from `localizeHref` (isSlashedPath). */
export const AUDIENCE_DESTS: HubDest[] = AUDIENCE_HUBS;
