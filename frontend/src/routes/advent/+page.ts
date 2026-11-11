import { ADVENT_BOOKS, ADVENT_PLAN, ADVENT_SERMONS } from '$lib/advent';
import { getPlan, listBooks, listSermons } from '$lib/library-public';
import { loadShelf } from '$lib/loadShelf';
import type { PageLoad } from './$types';

// The Advent hub ($lib/advent): the season's plan, then books and sermons for
// it. English-only, like /quotes — the plan reads books that exist only in
// English. Prerenders to /advent/index.html, so its links carry the slash.
export const prerender = true;
export const trailingSlash = 'always';

/** `slugs`' rows out of a shelf, in the hand-picked order; missing ones drop. */
const pick = <T extends { slug: string }>(rows: T[], slugs: string[]) =>
	slugs.flatMap((s) => rows.filter((r) => r.slug === s));

export const load: PageLoad = async ({ fetch }) => {
	// The plan leads the page, but a plan the API doesn't serve yet (a deploy
	// lagging this build) only drops that block: the shelves still stand.
	const [plan, books, sermons] = await Promise.all([
		getPlan(ADVENT_PLAN, 'en', fetch).catch(() => null),
		loadShelf(listBooks('en', fetch)),
		loadShelf(listSermons('en', fetch))
	]);
	return {
		plan,
		books: pick(books.items, ADVENT_BOOKS),
		sermons: pick(sermons.items, ADVENT_SERMONS),
		loadError: books.loadError && sermons.loadError && !plan
	};
};
