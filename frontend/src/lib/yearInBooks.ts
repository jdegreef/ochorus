import type { BookSummary } from './library-public';
import type { ProgressRecord, WorkKind } from './reading-schema';
import { longestStreak } from './streak';

/**
 * "Your year in books" — the Bookshelf's yearly summary, built from what the
 * device already holds: finished stamps on reading positions (synced), the
 * per-day activity log (synced, the streak's source) and the reader's
 * measured pace.
 *
 * Only BOOKS count toward the year: a sermon or biography also carries a
 * finished stamp, but "12 books this year" means books.
 *
 * Hours are an ESTIMATE, and the page says so: the words in the books finished
 * that year at the reader's own pace. Sittings are recorded on the server
 * (ReadingSession) but not readable back yet, and they'd miss offline reading
 * anyway.
 */

type ProgressRow = ProgressRecord & { slug: string; kind: WorkKind };

export interface YearStats {
	year: number;
	/** Books finished that year — every stamp, including a book with no row in
	 *  this language (which can't show a cover). */
	finished: number;
	/** The finished books this language can draw, most recently finished first. */
	books: BookSummary[];
	/** Words in `books` — the basis of the hours estimate. */
	words: number;
	/** Estimated reading hours (rounded); `words > 0 && hours === 0` = under one. */
	hours: number;
	daysRead: number;
	longestStreak: number;
	/** The author with the most books finished that year — only when someone
	 *  actually leads with two or more; with every author on one book it would
	 *  just be whoever came last, which isn't "most-read". */
	topAuthor: { name: string; slug: string; count: number } | null;
}

/** The local calendar year of an epoch-ms time. */
export const yearOf = (ms: number) => new Date(ms).getFullYear();

export function yearStats({
	progress,
	books,
	days,
	year,
	wpm
}: {
	progress: ProgressRow[];
	books: BookSummary[];
	days: Iterable<string>;
	year: number;
	wpm: number;
}): YearStats {
	const bySlug = new Map(books.map((b) => [b.slug, b]));
	const done = progress
		.filter((p) => p.kind === 'book' && p.finished_at != null && yearOf(p.finished_at) === year)
		.sort((a, b) => (b.finished_at ?? 0) - (a.finished_at ?? 0));

	const shown = done.flatMap((p) => {
		const b = bySlug.get(p.slug);
		return b ? [b] : [];
	});
	const words = shown.reduce((sum, b) => sum + (b.word_count ?? 0), 0);

	// Most-read author: most books, ties to whoever was finished most recently
	// (`shown` is newest first, so the first to reach the top count wins).
	const counts = new Map<string, { name: string; slug: string; count: number }>();
	for (const b of shown) {
		const c = counts.get(b.author.slug) ?? { name: b.author.name, slug: b.author.slug, count: 0 };
		c.count += 1;
		counts.set(b.author.slug, c);
	}
	let topAuthor: YearStats['topAuthor'] = null;
	for (const c of counts.values()) if (!topAuthor || c.count > topAuthor.count) topAuthor = c;
	if (topAuthor && topAuthor.count < 2) topAuthor = null;

	const prefix = `${year}-`;
	const yearDays = [...days].filter((d) => d.startsWith(prefix));

	return {
		year,
		finished: done.length,
		books: shown,
		words,
		hours: wpm > 0 ? Math.round(words / wpm / 60) : 0,
		daysRead: new Set(yearDays).size,
		longestStreak: longestStreak(yearDays),
		topAuthor
	};
}

/** Every year with something to show — a finished book or a day read — newest
 *  first, always including the current year (where the goal lives). */
export function yearsWithData(
	progress: ProgressRow[],
	days: Iterable<string>,
	currentYear: number
): number[] {
	const years = new Set<number>([currentYear]);
	for (const p of progress) if (p.kind === 'book' && p.finished_at != null) years.add(yearOf(p.finished_at));
	for (const d of days) {
		const y = Number(d.slice(0, 4));
		if (Number.isInteger(y) && y > 1900) years.add(y);
	}
	return [...years].filter((y) => y <= currentYear).sort((a, b) => b - a);
}

export type PaceStatus = 'met' | 'ahead' | 'on' | 'behind';

/**
 * Where the reader stands against a yearly goal on `today` ('YYYY-MM-DD').
 * The target by today is the goal spread evenly over the year, rounded DOWN —
 * so on 23 September a 12-book goal expects 8, and 8 is "on pace". A past year
 * is judged on the whole goal. `by` is how many books ahead or behind.
 */
export function goalPace(
	done: number,
	goal: number,
	today: string,
	year: number
): { status: PaceStatus; by: number } {
	if (done >= goal) return { status: 'met', by: 0 };
	const todayYear = Number(today.slice(0, 4));
	let expected = goal;
	if (year === todayYear) {
		const start = Date.UTC(year, 0, 1);
		const end = Date.UTC(year + 1, 0, 1);
		const now = Date.parse(today + 'T00:00:00Z') + 86_400_000; // count today
		expected = Math.floor((goal * (now - start)) / (end - start));
	}
	if (done > expected) return { status: 'ahead', by: done - expected };
	if (done === expected) return { status: 'on', by: 0 };
	return { status: 'behind', by: expected - done };
}
