import { building } from '$app/environment';
import { listBooks, listAuthors, listTopics, listSermons } from '$lib/library-public';
import { pickByDay, dayNumber } from '$lib/dailyPicks';
import { isPlateCover } from '$lib/coverArt';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

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

// NOTE: this page is prerendered — only PUBLIC data belongs here. Personal
// blocks (Continue reading, Today's reading) fetch client-side in their
// components so the baked HTML is the same for everyone.
export const load: PageLoad = async () => {
	const [books, authors, topics, sermons] = await Promise.all([
		shelf(listBooks(getLang())),
		// The endpoint defaults to `en`, so calling it bare gave EVERY locale's
		// home page the English roster — with English book counts, which the
		// `book_count > 0` filter below then trusted. AuthorListView is
		// per-language on both counts (an author earns a place by having a work
		// or a readable bio in that language), so the locale has to be passed.
		shelf(listAuthors(getLang())),
		// Topics stay tolerant even during the build: they are a decorative
		// cross-navigation row, and the page below already hides the section
		// when there are none.
		listTopics(getLang()).catch(() => []),
		// Fetched only for the library-breadth count under the hero — tolerant at
		// runtime, so a 0 just drops the sermon figure rather than breaking home.
		shelf(listSermons(getLang()))
	]);
	return {
		books,
		// Library breadth for the hero's social-proof line. Counts of what this
		// LANGUAGE actually has (the lists are already per-locale), so a locale
		// with fewer works advertises its own honest numbers, not English's.
		counts: { books: books.length, authors: authors.length, sermons: sermons.length },
		// Six books that favour six DIFFERENT authors. `books.slice(0, 6)` took
		// the API's own order, which groups by writer — so the front of the
		// library was routinely three Murrays and three Spurgeons.
		//
		// Picked HERE rather than in the component, even though `load` runs at
		// build time and therefore rotates per deploy rather than per calendar
		// day: this page is prerendered, so a client-side pick would swap all
		// six cards at hydration, in view, on the site's front page. A shelf
		// that changes with each deploy and never clusters is the better trade.
		//
		// Only books with real cover art reach this editorial shelf: a generated
		// flat plate (the `.svg` tier — see `isPlateCover`) reads as half-finished
		// on the front page beside a painting or a photograph. Filtered BEFORE
		// `pickByDay`, so the six still favour six different authors. `books` is
		// returned unfiltered above, so Continue-reading (which reads that list,
		// not `featured`) still lands a returning reader on their own book —
		// plate cover or not.
		featured: pickByDay(
			books.filter((b) => !isPlateCover(b.cover_url)),
			6,
			dayNumber(),
			(b) => b.author.slug
		),
		// Most-published first (name breaks ties, so the cap is stable across
		// builds) — if only eight authors fit, they should be the substantial ones.
		authors: authors
			.filter((a) => a.book_count > 0)
			.sort((a, b) => b.book_count - a.book_count || a.name.localeCompare(b.name))
			.slice(0, AUTHOR_LIMIT),
		topics: topics
			.filter((topic) => topic.book_count > 0)
			.sort(
				(a, b) =>
					b.book_count + b.sermon_count - (a.book_count + a.sermon_count) ||
					a.title.localeCompare(b.title)
			)
			.slice(0, HOME_TOPIC_LIMIT)
	};
};
