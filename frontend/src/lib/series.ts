import * as m from '$lib/paraglide/messages.js';
import { volumeNumeral } from '$lib/coverStyles';
import type { BookSeries, BookSummary } from '$lib/library-public';

/**
 * The book page's one-line series label: "Book 2 of 6 in Rooted" for an
 * ordered series, "Part of The Key Teachings" for a collection.
 *
 * The numbers go through `volumeNumeral`, the call the cover's own ring makes,
 * so a Persian page says ۲ in both places rather than a ring and a sentence
 * that disagree about digits.
 */
export function seriesLabel(series: BookSeries, language: string): string {
	const position = volumeNumeral(series.position, language);
	if (!position) return m.book_series_member({ series: series.title });
	return m.book_series_volume({
		position,
		total: volumeNumeral(series.total, language) ?? String(series.total),
		series: series.title
	});
}

/** What a reader already has of a book, as `$lib/progress` records it. */
export interface BookProgress {
	started: boolean;
	finished: boolean;
}

/**
 * The series page's one action: which book to open, and whether that is a
 * start or a return. A book begun and not finished comes first — a reader who
 * jumped to volume 3 is going back to volume 3, not being sent to volume 1 —
 * then the first unfinished one in order. Null once every book is finished.
 */
export function nextInSeries(
	books: BookSummary[],
	progressOf: (slug: string) => BookProgress
): { book: BookSummary; resume: boolean } | null {
	const reading = books.find((b) => {
		const p = progressOf(b.slug);
		return p.started && !p.finished;
	});
	if (reading) return { book: reading, resume: true };
	const next = books.find((b) => !progressOf(b.slug).finished);
	return next ? { book: next, resume: false } : null;
}
