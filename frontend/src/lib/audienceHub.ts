import type { IconName } from '$lib/components/Icon.svelte';
import type { AudienceShelf, BookSummary, HubAudience } from './library-public';

/**
 * The young-reader hubs — /young-readers/ and /teens/ — one front door each to
 * what /series, /originals, /topics and /plans each hold a part of. The page is
 * one component (`AudienceHub.svelte`) driven by this table; the data is one
 * call (`getAudienceShelf`), so a new retelling, series or plan for either
 * audience lands on its hub with no edit here.
 *
 * Two hubs, not one "Kids" page: the young-readers hub speaks to the adult who
 * chooses for a child, the teens hub to the teenager choosing for themselves.
 */
export interface AudienceHubConfig {
	audience: HubAudience;
	/** Unlocalized, unslashed — `localizeHref` adds the slash (isSlashedPath). */
	path: string;
	/** The nav word: the `<h1>`, the `<title>`, and every link to the page. */
	labelKey: string;
	/** Its tile in the phone's More sheet. */
	icon: IconName;
	/**
	 * "Start here", in order of preference — the first one this language has.
	 * Slugs, not a flag on the book: which book a newcomer should meet first is
	 * an editor's call, and a missing one falls through to the next, then to the
	 * hub's first book, so a language without these still gets a pick.
	 */
	starts: string[];
}

export const YOUNG_READERS_HUB: AudienceHubConfig = {
	audience: 'young_readers',
	path: '/young-readers',
	labelKey: 'nav.youngReaders',
	icon: 'sun',
	starts: ['pilgrims-progress-children', 'pilgrims-progress-words-of-one-syllable']
};

export const TEENS_HUB: AudienceHubConfig = {
	audience: 'teens',
	path: '/teens',
	labelKey: 'nav.teens',
	icon: 'compass',
	starts: ['around-the-wicket-gate', 'pilgrims-progress-teens', 'all-of-grace']
};

export const AUDIENCE_HUBS: AudienceHubConfig[] = [YOUNG_READERS_HUB, TEENS_HUB];

/** Every book card the hub can show (series volumes are tiles, not cards). */
function hubBooks(shelf: AudienceShelf): BookSummary[] {
	return [...shelf.editions, ...shelf.more];
}

/** The one book to start with: the first preferred slug this language has,
 * else the hub's first book; null on an empty hub. */
export function startPick(shelf: AudienceShelf, starts: string[]): BookSummary | null {
	const books = hubBooks(shelf);
	const bySlug = new Map(books.map((b) => [b.slug, b]));
	for (const slug of starts) {
		const hit = bySlug.get(slug);
		if (hit) return hit;
	}
	return books[0] ?? null;
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
