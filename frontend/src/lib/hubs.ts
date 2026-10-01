import { error } from '@sveltejs/kit';
import {
	listAuthors,
	listBooks,
	listHubs,
	type AuthorBio,
	type BookSummary,
	type Hub,
	type HubChip
} from '$lib/library-public';
import { loadShelf } from '$lib/loadShelf';

/**
 * Biography hubs — writers grouped by tradition or by place (`Hub`). Pure
 * helpers shared by the hub pages, the biographies index and the author page.
 */

/** A hub's path: traditions under /tradition, regions and places under /place. */
export const hubPath = (h: Pick<HubChip, 'kind' | 'slug'>): string =>
	`/biographies/${h.kind === 'tradition' ? 'tradition' : 'place'}/${h.slug}`;

/** The hub a route shows, or undefined (→ 404) when it doesn't exist in this
 *  language or the slug belongs to the other route's kind. */
export const findHub = (hubs: Hub[], slug: string, route: 'tradition' | 'place'): Hub | undefined =>
	hubs.find((h) => h.slug === slug && (h.kind === 'tradition') === (route === 'tradition'));

/** The hub's writers as the Biographies page lists them, earliest-born first
 *  (undated sink to the end) — the era pages' order. */
export const hubWriters = (hub: Hub, authors: AuthorBio[]): AuthorBio[] => {
	const members = new Set(hub.members);
	return authors
		.filter((a) => members.has(a.slug))
		.sort((a, b) => (a.birth_year ?? 9999) - (b.birth_year ?? 9999) || a.name.localeCompare(b.name));
};

/**
 * "Where to start reading": each writer's first book, in the writers' order,
 * up to `limit`. One per writer, so a prolific author doesn't fill the row; the
 * shelf's own order (sort_order, then title) decides which of theirs leads.
 */
export const hubShelf = (writers: AuthorBio[], books: BookSummary[], limit = 6): BookSummary[] => {
	const first = new Map<string, BookSummary>();
	for (const b of books) if (!first.has(b.author.slug)) first.set(b.author.slug, b);
	return writers.flatMap((w) => first.get(w.slug) ?? []).slice(0, limit);
};

/** Places under a region, or the region and sibling places of a place. */
export const relatedPlaces = (hub: Hub, hubs: Hub[]): Hub[] => {
	if (hub.kind === 'region') return hubs.filter((h) => h.region === hub.slug);
	if (hub.kind === 'place' && hub.region)
		return hubs.filter(
			(h) => h.slug !== hub.slug && (h.slug === hub.region || h.region === hub.region)
		);
	return [];
};

/**
 * The index rows: each region with its places. A place whose region has no
 * page in this language (or that has no region) is not dropped: all such
 * places share one trailing group with no region heading ("Elsewhere").
 */
export type PlaceGroup = { region: Hub | null; places: Hub[] };

export const placeGroups = (hubs: Hub[]): PlaceGroup[] => {
	const regions = hubs.filter((h) => h.kind === 'region');
	const places = hubs.filter((h) => h.kind === 'place');
	const groups: PlaceGroup[] = regions.map((r) => ({
		region: r,
		places: places.filter((p) => p.region === r.slug)
	}));
	const shown = new Set(regions.map((r) => r.slug));
	const loose = places.filter((p) => !p.region || !shown.has(p.region));
	if (loose.length) groups.push({ region: null, places: loose });
	return groups;
};

/**
 * The shared loader of the two hub routes. A hub this language doesn't have is
 * a 404; a failed hub fetch propagates (the error page, not a false 404), as
 * the topic pages do. The writers are the primary list (`loadShelf` reports a
 * failure) and the books only feed the cover strips, so they degrade to none.
 * All three are requested together; only the hub list gates the page.
 */
export async function loadHub(
	route: 'tradition' | 'place',
	slug: string,
	lang: string,
	fetch: typeof globalThis.fetch
) {
	const shelf = loadShelf(listAuthors(lang, fetch));
	const booksP = listBooks(lang, fetch).catch(() => [] as BookSummary[]);
	const hubs = await listHubs(lang, fetch);
	const hub = findHub(hubs, slug, route);
	if (!hub) throw error(404, 'Unknown hub');
	const [{ items: authors, loadError }, books] = await Promise.all([shelf, booksP]);
	return { hub, hubs, authors, books, loadError };
}

/** The prerender entries for one hub route: every English hub of its kinds.
 *  Each locale's copy is reached from that locale's index and author pages. */
export async function hubEntries(route: 'tradition' | 'place') {
	try {
		const hubs = await listHubs('en');
		return hubs
			.filter((h) => (h.kind === 'tradition') === (route === 'tradition'))
			.map((h) => ({ slug: h.slug }));
	} catch {
		return [];
	}
}
