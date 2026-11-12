import { ADVENT_BOOKS, ADVENT_PLAN, ADVENT_SCRIPTURE_PLAN, ADVENT_SERMONS } from '$lib/advent';
import { getPlan, listBooks, listPlans, listSermons } from '$lib/library-public';
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
	const [plan, books, sermons, plans] = await Promise.all([
		getPlan(ADVENT_PLAN, 'en', fetch).catch(() => null),
		loadShelf(listBooks('en', fetch)),
		loadShelf(listSermons('en', fetch)),
		listPlans('en', fetch).catch(() => [])
	]);
	return {
		plan,
		// The Scripture plan's shelf card, or null while the API lacks it.
		scripturePlan: plans.find((p) => p.slug === ADVENT_SCRIPTURE_PLAN) ?? null,
		books: pick(books.items, ADVENT_BOOKS),
		sermons: pick(sermons.items, ADVENT_SERMONS),
		loadError: books.loadError && sermons.loadError && !plan
	};
};
