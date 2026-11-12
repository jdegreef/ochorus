/**
 * A plan day that reads several chapters of one book (`PlanDay.chapter_count`,
 * Bible in a Year): which chapters it covers, and where a reader on one of
 * them stands in it. Pure, so the reader page's plan strip is tested apart
 * from the page.
 */
import type { PlanDay } from './library-public';

type DaySpan = Pick<PlanDay, 'day' | 'book_slug' | 'chapter_order' | 'chapter_count' | 'article_slug'>;

/** The chapter orders a day reads, in order — empty on an article day.
 *  `chapter_count` is absent from an API predating it: one chapter. */
export function dayChapters(d: DaySpan): number[] {
	if (d.article_slug || d.chapter_order == null) return [];
	const n = Math.max(1, d.chapter_count ?? 1);
	return Array.from({ length: n }, (_, i) => d.chapter_order! + i);
}

/**
 * The plan day reading chapter `order` of book `slug`, when the reader is
 * following day `current` (0 for none). Only that day or a neighbour of it: a
 * plan can put an article between two chapters, and the book's own Next must
 * not jump past it.
 */
export function planDayCovering<D extends DaySpan>(
	days: readonly D[],
	slug: string,
	order: number,
	current: number
): D | null {
	const d = days.find((x) => x.book_slug === slug && dayChapters(x).includes(order));
	if (!d || (current && d.day !== current && Math.abs(d.day - current) !== 1)) return null;
	return d;
}

/**
 * Where chapter `order` sits in a several-chapter day: its place (1-based),
 * the run's length, and the chapter after it in the day (null on the last).
 * Null for a one-chapter day, or a chapter the day does not read — those
 * finish the day where they stand.
 */
export function runStep(d: DaySpan, order: number): { n: number; m: number; next: number | null } | null {
	const run = dayChapters(d);
	const i = run.indexOf(order);
	if (run.length < 2 || i < 0) return null;
	return { n: i + 1, m: run.length, next: run[i + 1] ?? null };
}
