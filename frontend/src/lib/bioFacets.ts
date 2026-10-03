import { eraById, eraOf, type EraId } from '$lib/eras';
import { queryChip, type FilterChip } from '$lib/filterChips';
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
	if (skip !== 'era' && f.era.length && !f.era.includes(eraOf(a.birth_year)))
		return false;
	return true;
}

/**
 * How many writers each option of `facet` would show, given everything else
 * that is narrowing the list — the number beside a tick is what ticking it
 * (alone, within its facet) gives you. `authors` is the roster already narrowed
 * by the page's other filters (search, has-books, full life).
 */
export function facetCounts(
	authors: AuthorBio[],
	f: Facets,
	members: Map<string, Set<string>>,
	facet: FacetKey,
	options: string[]
): Map<string, number> {
	const pool = authors.filter((a) => inFacets(a, f, members, facet));
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

/**
 * The URL rewrites that bring the facet params in line with what parseFacets
 * kept: a value this language can't show (a hub that only exists in English,
 * from a shared link), a repeat, a blank. Only the keys that change are
 * returned, so applying an empty result writes nothing — the page runs this in
 * an effect, and a no-op write would schedule a navigation for no reason.
 * Without it a dropped value would still count as "filtered" (the summary and
 * the badge would show) with no chip to lift it.
 */
export function cleanFacetValues(
	raw: Record<FacetKey, string>,
	f: Facets
): Partial<Record<FacetKey, string>> {
	const out: Partial<Record<FacetKey, string>> = {};
	for (const k of ['trad', 'place', 'era'] as const) {
		const clean = f[k].join(',');
		if (clean !== raw[k]) out[k] = clean;
	}
	return out;
}

/** The biographies page's URL-backed filter values, as `urlFilters` holds them. */
export type BioFilterValues = Record<FacetKey, string> & {
	q: string;
	/** 'all' | 'library' (the has-books switch) | 'bio' (old links only). */
	filter: string;
	full: string;
};

/**
 * The removable chips for everything narrowing the roster, in the order the
 * controls sit: the query, has-books (or a legacy ?filter=bio), Full life, then
 * one chip per tradition, place and era value. Each chip's × lifts just that
 * value, writing straight into `values` (the live urlFilters state).
 *
 * `labels` maps `facet:value` to a display label; a value missing from it (no
 * option renders it) falls back to the raw slug rather than vanishing. The
 * Full-life chip follows the same `showFullLife` guard as its control.
 */
export function bioChips(
	values: BioFilterValues,
	f: Facets,
	ctx: {
		labels: Map<string, string>;
		showFullLife: boolean;
		t: (key: string) => string;
	}
): FilterChip[] {
	const c: FilterChip[] = [];
	const q = queryChip({ values });
	if (q) c.push(q);
	// 'bio' has no control of its own any more — only an old shared link sets it.
	if (values.filter !== 'all')
		c.push({
			kind: 'filter',
			label: ctx.t(values.filter === 'bio' ? 'bios.filterBioOnly' : 'bios.filterInLibrary'),
			onRemove: () => (values.filter = 'all')
		});
	if (ctx.showFullLife && values.full === '1')
		c.push({ kind: 'full', label: ctx.t('bios.fullLife'), onRemove: () => (values.full = '') });
	for (const k of ['trad', 'place', 'era'] as const)
		for (const v of f[k])
			c.push({
				kind: `${k}:${v}`,
				label: ctx.labels.get(`${k}:${v}`) ?? v,
				onRemove: () => (values[k] = toggleIn(values[k], v))
			});
	return c;
}
