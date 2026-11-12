import { building } from '$app/environment';
import {
	listBooks,
	listAuthors,
	listTopics,
	listSermons,
	AUTHOR_TILE_KEYS,
	pick,
	toCoverBook,
	toCoverFace,
	TOPIC_COUNT_KEYS,
	type AuthorBio,
	type AuthorTileData,
	type BookSummary,
	type CoverBook,
	type CoverFace,
	type HubAudience,
	type SermonSummary,
	type TopicCount,
	type TopicSummary
} from '$lib/library-public';
import { pickByDay, dayNumber } from '$lib/dailyPicks';
import { isPlateCover } from '$lib/coverArt';
import { editionKind } from '$lib/edition';
import { AUDIENCE_HUBS } from '$lib/audienceHub';
import { hubLanguages } from '$lib/audienceHubData';
import { tonightPool, type TonightItem } from '$lib/tonightShelf';
import { availableNeeds } from '$lib/needFinder';

/**
 * The home page's public shelves — the hero's covers, Discover, the authors grid, the topic chips
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
 * snapshot, byte for byte. It is small: five hero covers, six books, eight authors and eight
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
	/** The logged-out hero's covers (`HomeIntro`): three — the curated
	 *  `HERO_SLUGS` this language has, filled from its other painted books
	 *  (`CoverStrip`'s spread; fewer to be had → the deck). */
	hero: CoverFace[];
	/** The signed-in dashboard's Discover shelf (it has no hero). */
	featured: CoverBook[];
	/** The logged-out home's Discover shelf, right under the hero: `featured`'s
	 *  pick with the hero's books left out and its authors avoided. */
	discover: CoverBook[];
	authors: AuthorTileData[];
	topics: TopicCount[];
	/** The library's totals in this language — /about's stats band reads them. */
	counts: { books: number; sermons: number };
	/** The young-reader hubs with something to show in this language — the
	 *  home page links only those (`HomeAudienceHubs`). */
	audiences: HubAudience[];
	/** "Tonight, under 20 minutes" — short whole works in this language; the
	 *  browser shows them in the evening only (`$lib/tonightShelf`). */
	tonight: TonightItem[];
	/** "What do you need today?": the situations this language's topic shelves
	 *  can answer (`availableNeeds`, from the FULL topic list — the chips above
	 *  are capped). Ids only: the picks load when a chip is pressed. Optional:
	 *  a snapshot from before the finder reads as none, and the home falls back
	 *  to the topic chips. */
	needs?: string[];
}

/**
 * How many author cards the home grid shows before "All biographies →".
 * Two full rows at `lg:grid-cols-4`. Uncapped, the grid grew with the library
 * and buried everything under it — while the shelf above it showed six books.
 */
const AUTHOR_LIMIT = 8;

/**
 * The classics the home hero fans out, in the fan's left-to-right order — the
 * MIDDLE one stands in front (`CoverStrip`'s spread). Books every reader has
 * heard of, so the picture says "the library" before a word is read. A
 * language without one of them fills its place from its own painted books
 * (different authors first), so every locale's hero has a full fan.
 */
export const HERO_SLUGS = ['confessions', 'pilgrims-progress', 'the-imitation-of-christ'] as const;
const HERO_COUNT = HERO_SLUGS.length;

/**
 * How many topic chips the home "Browse by topic" row shows before
 * "All topics →". Uncapped, the row printed every shelf with content — 20+
 * pills — which on a phone became a wall that buried the whole page below it.
 * The chip row is a teaser; the full grid lives at /topics, where the section
 * header's link already points. Richest shelves first (members = books +
 * sermons, title breaking ties so the cap is stable across builds), so the
 * few that show are the most useful ones.
 *
 * Thirteen is two FULL lines at the default page width (76rem: 7 + 6 chips
 * with today's English titles); eight left a lone chip on a second line.
 * Phones and tablets show a prefix of the same list (`TopicChips` hides the
 * tail below `sm` / `lg`), so the row stays a teaser there, not a wall.
 */
const HOME_TOPIC_LIMIT = 13;

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

const authorTile = (a: AuthorBio): AuthorTileData => pick(a, AUTHOR_TILE_KEYS);
const topicCount = (t: TopicSummary): TopicCount => pick(t, TOPIC_COUNT_KEYS);

/** The snapshot's derivation, pure so it can be tested without an API. */
export function deriveHomeShelves(
	lists: {
		books: BookSummary[];
		authors: AuthorBio[];
		topics: TopicSummary[];
		sermons: SermonSummary[];
		audiences?: HubAudience[];
	},
	day: number,
	language = 'en'
): HomeShelves {
	const { books, authors, topics, sermons, audiences = [] } = lists;
	// Only books with real cover art reach the front page: a generated flat
	// plate (the `.svg` tier — see `isPlateCover`) reads as half-finished on
	// the front page beside a painting or a photograph.
	const painted = books.filter((b) => !isPlateCover(b.cover_url));
	const hero = heroBooks(painted, day);
	// Six books that favour six DIFFERENT authors. `books.slice(0, 6)` took
	// the API's own order, which groups by writer — so the front of the
	// library was routinely three Murrays and three Spurgeons. Painted covers
	// only, filtered BEFORE `pickByDay`, so the six still favour six authors.
	const pickSix = (pool: BookSummary[], avoid: string[] = []) =>
		pickByDay(pool, 6, day, (b) => b.author.slug, avoid).map(toCoverBook);
	return {
		hero: hero.map(toCoverFace),
		featured: pickSix(painted),
		// Under the hero: none of the books it fans out, and other writers
		// first, so the first two blocks of the page never repeat each other.
		discover: pickSix(
			painted.filter((b) => !hero.includes(b)),
			hero.map((b) => b.author.slug)
		),
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
		// Library breadth for /about's stats band. Counts of what this LANGUAGE
		// actually has (the lists are already per-locale), so a locale with
		// fewer works states its own honest numbers, not English's.
		counts: { books: books.length, sermons: sermons.length },
		audiences,
		tonight: tonightPool({ books, sermons, authors }, language, day),
		needs: availableNeeds(topics)
	};
}

/** The hero's three: the curated classics this language has, in their places,
 *  each missing one filled by another painted full-text book (never a
 *  young-reader edition) — by an author the fan does not have yet where it
 *  can. The snapshot holds exactly what the hero shows. */
function heroBooks(painted: BookSummary[], day: number): BookSummary[] {
	const bySlug = new Map(painted.map((b) => [b.slug, b]));
	const curated = HERO_SLUGS.map((slug) => bySlug.get(slug));
	const have = curated.filter((b): b is BookSummary => !!b);
	const fill = pickByDay(
		painted.filter((b) => !have.includes(b) && !editionKind(b.slug)),
		HERO_COUNT - have.length,
		day,
		(b) => b.author.slug,
		have.map((b) => b.author.slug)
	);
	return curated.map((b) => b ?? fill.shift()).filter((b): b is BookSummary => !!b);
}

/** Fetch the four lists for `lang` and derive the snapshot, seeded with today. */
export async function homeShelves(lang: string): Promise<HomeShelves> {
	const [books, authors, topics, sermons, audiences] = await Promise.all([
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
		// For the library-breadth count /about shows and the "Tonight" pool —
		// tolerant at runtime, so an empty list just drops the sermon figure and
		// the sermon cards rather than breaking the page.
		shelf(listSermons(lang)),
		// The hubs this language has something in — tolerant even while
		// building, like topics: a decorative link band that simply hides.
		hubLanguages().then((has) =>
			AUDIENCE_HUBS.filter((h) => has[h.audience].includes(lang)).map((h) => h.audience)
		)
	]);
	return deriveHomeShelves({ books, authors, topics, sermons, audiences }, dayNumber(), lang);
}
