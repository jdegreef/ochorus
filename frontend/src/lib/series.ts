import * as m from '$lib/paraglide/messages.js';
import { volumeNumeral } from '$lib/coverStyles';
import type { BookSeriesLine, BookSummary } from '$lib/library-public';

/**
 * The book page's one-line series label: "Book 2 of 6 in Rooted" for an
 * ordered series, "Part of The Key Teachings" for a collection.
 *
 * The numbers go through `volumeNumeral`, the call the cover's own ring makes,
 * so a Persian page says ۲ in both places rather than a ring and a sentence
 * that disagree about digits.
 */
export function seriesLabel(series: BookSeriesLine, language: string): string {
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

/** One by-series group on the Books shelf. */
export interface SeriesGroup<B> {
	slug: string;
	title: string;
	books: B[];
}

/**
 * The Books shelf's "By series" view: a group per series, in `order` (the
 * index's series order, by slug; a series missing from it goes last), each
 * group's books in reading order; then every book in no series, in the order
 * given. A collection keeps the order given too — the sort is stable and its
 * positions are all null.
 */
export function groupBySeries<B extends Pick<BookSummary, 'series'>>(
	books: B[],
	order: string[]
): { named: SeriesGroup<B>[]; standalone: B[] } {
	const rank = new Map(order.map((slug, i) => [slug, i]));
	const bySlug = new Map<string, SeriesGroup<B>>();
	const standalone: B[] = [];
	for (const b of books) {
		if (!b.series) {
			standalone.push(b);
			continue;
		}
		const g = bySlug.get(b.series.slug) ?? { slug: b.series.slug, title: b.series.title, books: [] };
		g.books.push(b);
		bySlug.set(b.series.slug, g);
	}
	const named = [...bySlug.values()].sort(
		(a, b) => (rank.get(a.slug) ?? rank.size) - (rank.get(b.slug) ?? rank.size)
	);
	for (const g of named) g.books.sort((a, b) => (a.series?.position ?? 0) - (b.series?.position ?? 0));
	return { named, standalone };
}
