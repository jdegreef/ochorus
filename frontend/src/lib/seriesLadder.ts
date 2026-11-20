import type { SeriesSummary } from '$lib/library-public';

/**
 * The /series reading ladder: the series as rungs from the youngest reader to
 * an adult — "start where your reader is, and climb". A young-reader or teens
 * series stands on the rung of its own lowest age (a teens series with no age
 * on the teens' lowest, else 13); the adults' series share a top rung, the
 * first few only (the ladder points up, the shelf below holds the rest).
 */
export interface Rung {
	/** The lowest age on the rung, or null for the adults' rung. */
	min: number | null;
	series: Pick<SeriesSummary, 'slug' | 'title'>[];
}

const TEENS_FLOOR = 13;
const ADULT_SERIES = 3;

export function readingLadder(series: SeriesSummary[]): Rung[] {
	const teens = series.filter((s) => s.audience === 'teens');
	const teensFloor = Math.min(
		...teens.map((s) => s.min_age ?? Infinity),
		TEENS_FLOOR
	);
	const byAge = new Map<number, Rung>();
	for (const s of series) {
		if (s.audience !== 'young_readers' && s.audience !== 'teens') continue;
		const min = s.min_age ?? (s.audience === 'teens' ? teensFloor : null);
		if (min == null) continue;
		if (!byAge.has(min)) byAge.set(min, { min, series: [] });
		byAge.get(min)!.series.push({ slug: s.slug, title: s.title });
	}
	const rungs = [...byAge.values()].sort((a, b) => a.min! - b.min!);
	const adults = series.filter((s) => s.audience === 'adults').slice(0, ADULT_SERIES);
	if (adults.length) rungs.push({ min: null, series: adults.map(({ slug, title }) => ({ slug, title })) });
	return rungs;
}
