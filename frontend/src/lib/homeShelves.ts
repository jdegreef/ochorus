import { building } from '$app/environment';
import {
	listBooks,
	listAuthors,
	listTopics,
	listSermons,
	AUTHOR_TILE_KEYS,
	COVER_AUTHOR_KEYS,
	COVER_BOOK_DROPS,
	TOPIC_COUNT_KEYS,
	type AuthorBio,
	type AuthorTileData,
	type BookSummary,
	type CoverBook,
	type TopicCount,
	type TopicSummary
} from '$lib/library-public';
import { pickByDay, dayNumber } from '$lib/dailyPicks';
import { isPlateCover } from '$lib/coverArt';

/**
 * The home page's public shelves — Discover, the authors grid, the topic chips
 * and the hero's library counts — as ONE snapshot taken when the site is built.
 *
 * WHY A SNAPSHOT. The home page is prerendered, and its universal `load` runs
 * again in the browser at hydration. Deriving these there, from a fresh fetch,
 * meant the second run could choose different items than the HTML: another
 * day's seed for Discover, or a book published since the build shifting the
 * pick and reordering the authors grid (it is sorted by live book counts).
 * Svelte then repairs text and links but keeps each `<img>`'s server `src`, so
 * cards showed one book's cover — or one author's face — under another's name.
 *
 * So `routes/home-shelves/[lang].json` serves this at build time, and the home
 * `load` reads it through SvelteKit's `fetch`, which inlines the response into
 * the prerendered page and replays it at hydration. Both runs see the same
 * snapshot, byte for byte. It is small: six books, eight authors and eight
 * topics, each PROJECTED to the fields the page draws (`CoverBook`,
 * `AuthorTileData`, `TopicCount`) — whole API objects carried every author's
 * bio and every topic's cover list, and the four full lists would have added
 * about 86 KB gzipped to a 12 KB front page.
 *
 * The shelves and counts are the BUILD's, on every home visit — including a
 * client-side navigation home, which reads the same static file. So a book
 * published between deploys reaches the home page with the next deploy, as it
 * reaches the prerendered HTML. That is the trade: a front page that never
 * disagrees with itself, rotated per deploy rather than per calendar day.
 */
export interface HomeShelves {
	featured: CoverBook[];
	authors: AuthorTileData[];
	topics: TopicCount[];
	counts: { books: number; authors: number; sermons: number };
}

/**
 * How many author cards the home grid shows before "All biographies →".
 * Two full rows at `lg:grid-cols-4`. Uncapped, the grid grew with the library
 * and buried everything under it — while the shelf above it showed six books.
 */
const AUTHOR_LIMIT = 8;

/**
 * How many topic chips the home "Browse by topic" row shows before
 * "All topics →". Uncapped, the row printed every shelf with content — 20+
 * pills — which on a phone became a wall that buried the whole page below it.
 * The chip row is a teaser; the full grid lives at /topics, where the section
 * header's link already points. Richest shelves first (members = books +
 * sermons, title breaking ties so the cap is stable across builds), so the
 * few that show are the most useful ones.
 */
const HOME_TOPIC_LIMIT = 8;

/**
 * Tolerate a failed shelf at RUNTIME, never while building.
 *
 * The two contexts want opposite things from the same error. During the build
 * a swallowed failure is the worst outcome available: the homepage prerenders
 * with an empty shelf, ships, and looks deliberate — nothing is red, and the
 * site simply has no books on its front page until someone notices. At runtime
 * — a client-side navigation home, a reader who has gone offline — throwing
 * replaces a page whose chrome, nav and personal blocks all still work with a
 * full-page error. So: loud at build time, degraded at run time.
 */
const shelf = <T>(pending: Promise<T[]>): Promise<T[]> =>
	building ? pending : pending.catch(() => []);

/** `obj` with only `keys` — the runtime half of a narrow type built from them. */
function pick<T extends object, K extends keyof T>(obj: T, keys: readonly K[]): Pick<T, K> {
	return Object.fromEntries(keys.map((k) => [k, obj[k]])) as Pick<T, K>;
}

const coverBook = (b: BookSummary): CoverBook => {
	const book: Record<string, unknown> = { ...b, author: pick(b.author, COVER_AUTHOR_KEYS) };
	for (const k of COVER_BOOK_DROPS) delete book[k];
	return book as CoverBook;
};
const authorTile = (a: AuthorBio): AuthorTileData => pick(a, AUTHOR_TILE_KEYS);
const topicCount = (t: TopicSummary): TopicCount => pick(t, TOPIC_COUNT_KEYS);

/** The snapshot's derivation, pure so it can be tested without an API. */
export function deriveHomeShelves(
	lists: {
		books: BookSummary[];
		authors: AuthorBio[];
		topics: TopicSummary[];
		sermons: { length: number };
	},
	day: number
): HomeShelves {
	const { books, authors, topics, sermons } = lists;
	return {
		// Six books that favour six DIFFERENT authors. `books.slice(0, 6)` took
		// the API's own order, which groups by writer — so the front of the
		// library was routinely three Murrays and three Spurgeons.
		//
		// Only books with real cover art reach this editorial shelf: a generated
		// flat plate (the `.svg` tier — see `isPlateCover`) reads as half-finished
		// on the front page beside a painting or a photograph. Filtered BEFORE
		// `pickByDay`, so the six still favour six different authors.
		featured: pickByDay(
			books.filter((b) => !isPlateCover(b.cover_url)),
			6,
			day,
			(b) => b.author.slug
		).map(coverBook),
		// Most-published first (name breaks ties, so the cap is stable across
		// builds) — if only eight authors fit, they should be the substantial ones.
		authors: authors
			.filter((a) => a.book_count > 0)
			.sort((a, b) => b.book_count - a.book_count || a.name.localeCompare(b.name))
			.slice(0, AUTHOR_LIMIT)
			.map(authorTile),
		topics: topics
			.filter((topic) => topic.book_count > 0)
			.sort(
				(a, b) =>
					b.book_count + b.sermon_count - (a.book_count + a.sermon_count) ||
					a.title.localeCompare(b.title)
			)
			.slice(0, HOME_TOPIC_LIMIT)
			.map(topicCount),
		// Library breadth for the hero's social-proof line. Counts of what this
		// LANGUAGE actually has (the lists are already per-locale), so a locale
		// with fewer works advertises its own honest numbers, not English's.
		counts: { books: books.length, authors: authors.length, sermons: sermons.length }
	};
}

/** Fetch the four lists for `lang` and derive the snapshot, seeded with today. */
export async function homeShelves(lang: string): Promise<HomeShelves> {
	const [books, authors, topics, sermons] = await Promise.all([
		shelf(listBooks(lang)),
		// The endpoint defaults to `en`, so calling it bare gave EVERY locale's
		// home page the English roster — with English book counts, which the
		// `book_count > 0` filter then trusted. AuthorListView is per-language on
		// both counts (an author earns a place by having a work or a readable bio
		// in that language), so the locale has to be passed.
		shelf(listAuthors(lang)),
		// Topics stay tolerant even during the build: they are a decorative
		// cross-navigation row, and the page already hides the section when
		// there are none.
		listTopics(lang).catch(() => []),
		// Fetched only for the library-breadth count under the hero — tolerant at
		// runtime, so a 0 just drops the sermon figure rather than breaking home.
		shelf(listSermons(lang))
	]);
	return deriveHomeShelves({ books, authors, topics, sermons }, dayNumber());
}
