/**
 * Pure helpers for the admin audit's chapter-length chart: turn the API's
 * edges + counts into labelled, flag-aware buckets. Kept out of the component
 * so the edge arithmetic is unit-tested (an off-by-one here would paint a bar
 * amber that the checks don't flag).
 */
import type { ChapterLengths } from './library-admin';

export type LengthBucket = {
	/** Short axis label: "<150", "500–1k", "16k+". */
	label: string;
	/** Exact word range for the table and tooltip: "150–499 words". */
	range: string;
	count: number;
	/** Which check flags every chapter in it, if either. */
	flag: 'tiny' | 'giant' | null;
};

const nf = new Intl.NumberFormat('en');

/** 500 → "500", 1000 → "1k", 12000 → "12k", 1500 → "1.5k". */
export const compactWords = (n: number) => (n >= 1000 ? `${n / 1000}k` : String(n));

export function lengthBuckets(d: ChapterLengths): LengthBucket[] {
	const { edges, counts, tiny_max, giant_min } = d;
	return counts.map((count, i) => {
		const lo = i > 0 ? edges[i - 1] : null;
		const hi = i < edges.length ? edges[i] : null;
		const label =
			lo == null ? `<${compactWords(hi!)}` : hi == null ? `${compactWords(lo)}+` : `${compactWords(lo)}–${compactWords(hi)}`;
		// Mirrors backend qa.length_bucket: buckets are [lo, hi) below giant_min
		// and (lo, hi] from it, so the bucket closing on giant_min holds it —
		// exactly 8,000 words is NOT giant, and the exact range is what someone
		// tuning that threshold needs to read.
		const above = lo != null && lo >= giant_min;
		const first = lo == null ? 0 : above ? lo + 1 : lo;
		const last = hi == null ? null : hi >= giant_min ? hi : hi - 1;
		const range =
			lo == null
				? `Under ${nf.format(hi!)} words`
				: last == null
					? `Over ${nf.format(lo)} words`
					: `${nf.format(first)}–${nf.format(last)} words`;
		// The thresholds are edges, so a bucket is wholly on one side of each.
		const flag = hi != null && hi <= tiny_max ? 'tiny' : above ? 'giant' : null;
		return { label, range, count, flag };
	});
}

/** Index of the gap a threshold sits in: the line is drawn between bucket
 *  `i - 1` and bucket `i`. -1 if the value isn't an edge (never, from the API). */
export const edgeSlot = (d: ChapterLengths, value: number) => {
	const i = d.edges.indexOf(value);
	return i < 0 ? -1 : i + 1;
};

/**
 * The book page's "At a glance" bars: one per chapter, its height the
 * chapter's share of the longest (a floor keeps a two-line preface visible),
 * and the range in reading minutes for the caption. Null when a chart would
 * say nothing: fewer than three chapters with words, or more than `max` —
 * past that the bars are hairlines and the contents list says it better.
 */
export function chapterBars(
	words: number[],
	minutes: (w: number) => number,
	max = 60
): { heights: number[]; shortest: number; longest: number } | null {
	const counted = words.filter((w) => w > 0);
	if (counted.length < 3 || words.length > max) return null;
	const top = Math.max(...counted);
	return {
		heights: words.map((w) => (w > 0 ? Math.max(8, Math.round((w / top) * 100)) : 0)),
		shortest: minutes(Math.min(...counted)),
		longest: minutes(top)
	};
}
