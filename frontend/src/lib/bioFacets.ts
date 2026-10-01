import { eraById, eraOf, type EraId } from '$lib/eras';
import type { AuthorBio, Hub } from '$lib/library-public';

/**
 * The biographies index's three browse facets — tradition, place, era — as
 * in-page filters. Each is a multi-select kept in the URL as a comma list
 * (`?trad=puritans,methodists&place=wales&era=early`): ticks inside one facet
 * widen the list (any of them), facets narrow it against each other (all of
 * them), the way every faceted shelf reads.
 *
 * The hub pages (/biographies/tradition|place/<slug>) and the era pages stay —
 * they are the indexable answers — but on the index the same groupings now
 * filter in place rather than navigating away.
 */
/** One tick in a FacetMenu. `indent` nests a place under its region; `strong`
 *  marks the region. */
export type FacetOption = {
	v: string;
	label: string;
	count: number;
	indent?: boolean;
	strong?: boolean;
};

/** One card of the era band. */
export type EraCard = { id: EraId; name: string; range: string; count: number; faces: AuthorBio[] };

export type FacetKey = 'trad' | 'place' | 'era';
export type Facets = Record<FacetKey, string[]>;

/** A URL comma list → its values, blanks and repeats dropped. */
export const splitList = (s: string): string[] => [
	...new Set(
		s
			.split(',')
			.map((x) => x.trim())
			.filter(Boolean)
	)
];

/** Add `v` to a comma list, or take it out if it is there. */
export const toggleIn = (list: string, v: string): string => {
	const xs = splitList(list);
	return (xs.includes(v) ? xs.filter((x) => x !== v) : [...xs, v]).join(',');
};

/** Hub slug → the writers it lists. A region's list already includes its
 *  places' writers (the API resolves that), so a region tick needs no expansion. */
export const hubMembers = (hubs: Hub[]): Map<string, Set<string>> =>
	new Map(hubs.map((h) => [h.slug, new Set(h.members)]));

/**
 * The facets as the URL states them, with anything this language can't show
 * dropped — a hub slug with no hub here (a link shared from another locale), an
 * era id that isn't one. A dropped value must not narrow the list invisibly.
 */
export function parseFacets(
	raw: Record<FacetKey, string>,
	hubs: Hub[]
): Facets {
	const kinds = new Map(hubs.map((h) => [h.slug, h.kind]));
	return {
		trad: splitList(raw.trad).filter((s) => kinds.get(s) === 'tradition'),
		place: splitList(raw.place).filter((s) => {
			const k = kinds.get(s);
			return k === 'region' || k === 'place';
		}),
		era: splitList(raw.era).filter((e) => eraById(e))
	};
}

/** Does `a` pass every facet, optionally ignoring one (for that facet's counts)? */
export function inFacets(
	a: AuthorBio,
	f: Facets,
	members: Map<string, Set<string>>,
	skip?: FacetKey
): boolean {
	const anyHub = (slugs: string[]) => slugs.some((s) => members.get(s)?.has(a.slug));
	if (skip !== 'trad' && f.trad.length && !anyHub(f.trad)) return false;
	if (skip !== 'place' && f.place.length && !anyHub(f.place)) return false;
	if (skip !== 'era' && f.era.length && !f.era.includes(eraOf(a.birth_year) as EraId))
		return false;
	return true;
}

/**
 * How many writers each option of `facet` would show, given everything else
 * that is narrowing the list — the number beside a tick is what ticking it
 * (alone, within its facet) gives you. `base` is the rest of the page's filters
 * (search, has-books, full life).
 */
export function facetCounts(
	authors: AuthorBio[],
	f: Facets,
	members: Map<string, Set<string>>,
	facet: FacetKey,
	options: string[],
	base: (a: AuthorBio) => boolean
): Map<string, number> {
	const pool = authors.filter((a) => base(a) && inFacets(a, f, members, facet));
	const counts = new Map<string, number>(options.map((o) => [o, 0]));
	for (const a of pool) {
		const era = eraOf(a.birth_year);
		for (const o of options) {
			const hit = facet === 'era' ? o === era : members.get(o)?.has(a.slug);
			if (hit) counts.set(o, counts.get(o)! + 1);
		}
	}
	return counts;
}
