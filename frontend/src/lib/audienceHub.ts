import type { IconName } from '$lib/components/Icon.svelte';
import type { AudienceShelf, BookSummary, HubAudience } from './library-public';

/**
 * The young-reader hubs — /young-readers/ and /teens/ — one front door each to
 * what /series, /originals, /topics and /plans each hold a part of. The page is
 * one component (`AudienceHub.svelte`) driven by this table; the data is one
 * call (`$lib/audienceHubData`), so a new retelling, series or plan for either
 * audience lands on its hub with no edit here. Pure data and helpers — the nav
 * lists import it — so the loaders live in that module, not this one.
 *
 * Two hubs, not one "Kids" page: the young-readers hub speaks to the adult who
 * chooses for a child, the teens hub to the teenager choosing for themselves —
 * which is why each carries its own copy keys rather than sharing one voice.
 */
export interface AudienceHubConfig {
	audience: HubAudience;
	/** Unlocalized, unslashed — `localizeHref` adds the slash (isSlashedPath).
	 *  With `labelKey`, the shape of a `HubDest`, so the nav lists take it as is. */
	href: string;
	/** The nav word: the `<h1>`, the `<title>`, and every link to the page. */
	labelKey: string;
	/** Its tile in the phone's More sheet. */
	icon: IconName;
	/** The page's tagline; the home page's card line too. */
	taglineKey: string;
	/** What a search result shows: the `<title>` and the meta description, in
	 *  the words people search with ("free Christian books for children"). */
	seoTitleKey: string;
	seoDescriptionKey: string;
	/** The share button's words — who the page is passed on to. */
	shareKey: string;
	/** The line over the "Start here" pick. */
	startKey: string;
	/** The note under "Classics, retold". */
	retoldKey: string;
	/** Who the closing note is for, and what it suggests they do. */
	parentsHeadingKey: string;
	parentsTogetherKey: string;
	/** The /series audience group's link here. */
	seeKey: string;
}

export const YOUNG_READERS_HUB: AudienceHubConfig = {
	audience: 'young_readers',
	href: '/young-readers',
	labelKey: 'nav.youngReaders',
	icon: 'sun',
	taglineKey: 'audience.youngTagline',
	seoTitleKey: 'audience.youngSeoTitle',
	seoDescriptionKey: 'audience.youngSeoDescription',
	shareKey: 'audience.shareYoung',
	startKey: 'audience.startYoung',
	retoldKey: 'audience.retoldYoung',
	parentsHeadingKey: 'series.parentsHeading',
	parentsTogetherKey: 'audience.parentsTogetherYoung',
	seeKey: 'audience.seeYoung'
};

export const TEENS_HUB: AudienceHubConfig = {
	audience: 'teens',
	href: '/teens',
	labelKey: 'nav.teens',
	icon: 'compass',
	taglineKey: 'audience.teensTagline',
	seoTitleKey: 'audience.teensSeoTitle',
	seoDescriptionKey: 'audience.teensSeoDescription',
	shareKey: 'audience.shareTeens',
	startKey: 'audience.startTeens',
	retoldKey: 'audience.retoldTeens',
	parentsHeadingKey: 'audience.parentsTeensHeading',
	parentsTogetherKey: 'audience.parentsTogetherTeens',
	seeKey: 'audience.seeTeens'
};

export const AUDIENCE_HUBS: AudienceHubConfig[] = [YOUNG_READERS_HUB, TEENS_HUB];

/** The Plausible event a hub sends when its "Start here" is opened or it is
 *  shared — props `{ hub, action }`; its visits are the pageviews themselves. */
export const HUB_EVENT = 'Hub';

/** The hub for a series audience, if it has one (adults don't). */
export const hubFor = (audience: string | null | undefined): AudienceHubConfig | undefined =>
	AUDIENCE_HUBS.find((h) => h.audience === audience);

/** Every book card the hub shows (series volumes are tiles, not cards). */
export function hubBooks(shelf: AudienceShelf): BookSummary[] {
	return [...shelf.editions, ...shelf.more];
}

/** The "Start here" book — the API's pick (`AUDIENCE_STARTS`), as a card. */
export function startPick(shelf: AudienceShelf): BookSummary | null {
	return hubBooks(shelf).find((b) => b.slug === shelf.start) ?? null;
}

/** Books and series on the hub, for the header's counts line. */
export function hubCounts(shelf: AudienceShelf): { books: number; series: number } {
	const inSeries = shelf.series.reduce((n, s) => n + s.book_count, 0);
	return { books: inSeries + hubBooks(shelf).length, series: shelf.series.length };
}

/** Whether the hub has anything to show in this language. */
export function hubIsEmpty(shelf: AudienceShelf): boolean {
	return !shelf.series.length && !hubBooks(shelf).length;
}

export interface PrintableLink {
	/** Unlocalized. */
	href: string;
	label: string;
}

/**
 * The printable books, for the parents' note: a series with any printable
 * volume is ONE link to its page (Brave for God's four PDFs are one tag, not
 * four), and a stand-alone printable book links to itself. Series first, in
 * the hub's order, then books.
 */
export function printableLinks(shelf: AudienceShelf): PrintableLink[] {
	const printable = new Set(shelf.printable);
	const series = shelf.series
		.filter((s) => (s.books ?? []).some((slug) => printable.has(slug)))
		.map((s) => ({ href: `/series/${s.slug}/`, label: s.title }));
	const books = hubBooks(shelf)
		.filter((b) => printable.has(b.slug))
		.map((b) => ({ href: `/books/${b.slug}`, label: b.title }));
	return [...series, ...books];
}
