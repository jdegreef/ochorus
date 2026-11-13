import type { IconName } from '$lib/components/Icon.svelte';
import { ORIGINALS_PATH } from '$lib/originals';
import { AUDIENCE_HUBS } from '$lib/audienceHubs';
import { BIBLE_PATH, bibleIn } from '$lib/bible';

/**
 * The one ordered source for the reader-facing content-type lists.
 *
 * The top nav, the footer's link columns and the command palette each listed
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
	/** The section's printer's ornament (`<Fleuron ornament>`), drawn from
	 *  `/marks/ornament-<name>.svg`; its emblem is `/marks/emblem-<section>.svg`
	 *  (marks.test.ts checks both exist). Neither is drawn in the shelf's
	 *  `<PageHeader>` any more — design review #4 made the page head plain —
	 *  but the marks are the sections' identity and stay for other surfaces. */
	ornament: Ornament;
}

export type NavSection = 'books' | 'bible' | 'topics' | 'plans' | 'sermons' | 'biographies';

/** A section's ornament, in gold like every ornament (STYLE_GUIDE §1): a lamp
 *  for Books ("Thy word is a lamp", Ps 119:105), a scroll for the Bible ("in
 *  the volume of the book it is written of me", Heb 10:7), an anchor for Topics (hope,
 *  Heb 6:19), a vine for Plans (abiding, day by day, John 15), a descending
 *  dove for Sermons, a laurel for Biographies. 'leaf' is the house ornament,
 *  for every page that is not a section's. */
export type Ornament = 'leaf' | 'lamp' | 'scroll' | 'anchor' | 'vine' | 'dove' | 'laurel';

/** An English-only hub: the footer's More column and the palette, gated to
 *  English, and never the top nav (an entry point for search, not a primary
 *  journey). English-only because the content is lifted from / parsed against
 *  the English works, so there is no localized page to send anyone to. */
export interface HubDest {
	href: string;
	labelKey: string;
}

/** Books · Topics · Plans · Sermons · Biographies — the primary journeys every
 *  locale has. The chrome draws `primaryNav(locale)`, which adds the Bible where
 *  its books have shipped. */
export const PRIMARY_NAV: NavDest[] = [
	{ href: '/books', labelKey: 'nav.books', icon: 'book', section: 'books', ornament: 'lamp' },
	{ href: '/topics', labelKey: 'nav.topics', icon: 'tag', section: 'topics', ornament: 'anchor' },
	{ href: '/plans', labelKey: 'nav.plans', icon: 'calendar', section: 'plans', ornament: 'vine' },
	{ href: '/sermons', labelKey: 'nav.sermons', icon: 'mic', section: 'sermons', ornament: 'dove' },
	{ href: '/biographies', labelKey: 'nav.biographies', icon: 'users', section: 'biographies', ornament: 'laurel' }
];

/** The Bible — the Open Word Bible's books in canonical order (/bible/,
 *  `$lib/bible`). A primary section, but only in the locales whose Bible books
 *  have shipped (`bibleIn`): the page 404s elsewhere, so a link there would
 *  send the prerender crawl to a 404. It sits between Books and Topics — its 66
 *  books are kept off the Books shelves (`splitBible`), and this tab is where a
 *  reader finds them. The label is the tab's short word ("Bible"); the page's
 *  own title stays "The Bible" (`nav.bible`). The trailing slash comes from
 *  `localizeHref` (isSlashedPath). */
export const BIBLE_NAV: NavDest = {
	href: BIBLE_PATH,
	labelKey: 'nav.bibleTab',
	icon: 'scroll',
	section: 'bible',
	ornament: 'scroll'
};

/** Every section any locale can show — for what belongs to a section rather
 *  than to a menu (its marks, `sectionDest`). Menus draw `primaryNav`. */
export const SECTION_DESTS: NavDest[] = [PRIMARY_NAV[0], BIBLE_NAV, ...PRIMARY_NAV.slice(1)];

/** The primary journeys a reader in `locale` is offered, in order: Books, the
 *  Bible where its books have shipped, Topics, Plans, Sermons, Biographies. One
 *  gate for the top nav, the footer's Library column, the palette and the
 *  reader's site links, so the Bible is listed once, in the same place, on all
 *  of them. */
export function primaryNav(locale: string): NavDest[] {
	return bibleIn(locale) ? SECTION_DESTS : PRIMARY_NAV;
}

/** The sections the tablet bar (768–1023px) folds into its "More ▾" menu,
 *  their links hidden there by app.css (`a[data-section=…]`): the bar fits five
 *  words in one row, and these are the two it can spare. The Bible's tab is a
 *  desktop slot; a tablet reader meets it one tap away, first in More. */
export const TABLET_MORE_SECTIONS: readonly NavSection[] = ['bible', 'biographies'];

/** A section's entry — its icon, ornament and the rest. */
export const sectionDest = (section: NavSection): NavDest => SECTION_DESTS.find((d) => d.section === section)!;

/* Not listed here on purpose: the "Ochorus for …" landing pages ($lib/forLinks)
 * are pitches to a group of readers, not content destinations, so they sit in
 * the footer (one link to their /for/ hub) — not the palette or the More sheet. */

/** Articles · Scripture · Quotes · Glossary — English-only hubs (footer +
 *  palette). The glossary is the reader's tap-to-define words, one page each. */
export const ENGLISH_HUBS: HubDest[] = [
	{ href: '/articles', labelKey: 'nav.articles' },
	{ href: '/scripture', labelKey: 'reader.scripture' },
	{ href: '/quotes', labelKey: 'nav.quotes' },
	{ href: '/glossary', labelKey: 'nav.glossary' }
];

/** Book Series — every series in this language, hanging off Books. Not a top-nav
 *  slot (the Books page's rail and count link are its way in there), but every
 *  locale's footer More column and the palette offer it right after the
 *  primary journeys: a series is translated content, so each locale has its own
 *  index. The trailing slash is added by `localizeHref` ($lib/canonicalRedirect isSlashedPath). */
export const SERIES_DEST: HubDest = { href: '/series', labelKey: 'nav.series' };

/** Ochorus Originals — the house imprint's shelf. Not an English-only hub: its
 *  books are translated, so the footer and the palette offer it in every
 *  locale (the page lists only that language's books). Sits after the hubs, so
 *  English readers meet Articles · Scripture · Quotes · Originals · RSS. */
export const ORIGINALS_DEST: HubDest = { href: ORIGINALS_PATH, labelKey: 'nav.originals' };

/** The hub links every menu offers in `locale`: the English-only hubs. (The
 *  Bible was one until it became a primary section — `primaryNav`.) One gate
 *  for the footer, the palette, the tablet More menu and the phone's More
 *  sheet, which each turn these into links their own way. */
export function hubDests(locale: string): HubDest[] {
	return locale === 'en' ? ENGLISH_HUBS : [];
}

/** Authors & Books A–Z — the one page linking every writer and every book in
 *  a language ($lib/authorIndex), so the whole library is two clicks from any
 *  page. Every locale's footer More column and the palette offer it after
 *  Book Series. The trailing slash comes from `localizeHref` (isSlashedPath). */
export const AZ_INDEX_DEST: HubDest = { href: '/authors', labelKey: 'nav.azIndex' };

/** The young-reader hubs — /young-readers/ and /teens/ ($lib/audienceHub).
 *  Like Book Series, not a top-nav slot: every locale's footer More column,
 *  the palette and the phone's More sheet offer them right after Book Series
 *  (their books are translated, so each locale has its own copy). The trailing
 *  slash comes from `localizeHref` (isSlashedPath). */
export const AUDIENCE_DESTS: HubDest[] = AUDIENCE_HUBS;
