import * as m from '$lib/paraglide/messages.js';
import { volumeNumeral } from '$lib/coverStyles';
import type {
	BookSeriesLine,
	BookSummary,
	CoverBook,
	SeriesAudience,
	SeriesFor,
	SeriesSummary
} from '$lib/library-public';
import { contentLang } from '$lib/reading';

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

/** "2 of 6 read", its numbers in the page language's digits (as `seriesLabel`). */
export function seriesProgressLabel(done: number, total: number, language: string): string {
	return m.series_progress({
		done: volumeNumeral(done, language) ?? String(done),
		total: volumeNumeral(total, language) ?? String(total)
	});
}

/** A card's series line — `seriesLabel` in the book's own language — or "" for
 *  a book in no (named) series. BookCard and BookListRow both draw it. */
export function cardSeriesLine(book: Pick<CoverBook, 'series' | 'language'>): string {
	return book.series ? seriesLabel(book.series, contentLang(book.language)) : '';
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

/**
 * A reader's progress through a series, from its books' slugs: how many are
 * finished, and whether any is begun at all — the card draws nothing for a
 * series the reader has never opened.
 */
export function seriesProgress(
	slugs: string[],
	progressOf: (slug: string) => BookProgress
): { done: number; total: number; started: boolean } {
	const each = slugs.map(progressOf);
	return {
		done: each.filter((p) => p.finished).length,
		total: slugs.length,
		started: each.some((p) => p.started || p.finished)
	};
}

/**
 * The series that have a book among `books`, in `series`' own order — a topic's
 * series (on its page, or the Books shelf filtered to it), so a topic made of
 * series volumes leads with the series rather than a wall of volume covers.
 */
export function seriesAmong<S extends Pick<SeriesSummary, 'slug'>>(
	series: S[],
	books: Pick<BookSummary, 'series'>[]
): S[] {
	const present = new Set(books.map((b) => b.series?.slug).filter(Boolean));
	return series.filter((s) => present.has(s.slug));
}

/** Covers in a series card's fan — the API's `SeriesListView.COVERS`. */
const SERIES_FAN = 4;

/**
 * Series cards built from a shelf's own books — a topic page's "Book Series"
 * row, with no call for the series list (the prerender renders every topic in
 * every locale, and that crawl's API load is what once took the service down).
 * Each card's fan, count and progress come from the shelf's volumes of that
 * series, in reading order; there is no description, which the compact card
 * doesn't show.
 */
export function seriesFromBooks(
	books: Pick<BookSummary, 'slug' | 'title' | 'cover_url' | 'cover_color' | 'series'>[]
): SeriesSummary[] {
	return groupBySeries(books, []).named.map((g) => ({
		slug: g.slug,
		title: g.title,
		description: '',
		book_count: g.books.length,
		covers: g.books.slice(0, SERIES_FAN).map((b) => ({
			kind: 'book' as const,
			slug: b.slug,
			title: b.title,
			cover_url: b.cover_url,
			cover_color: b.cover_color
		})),
		books: g.books.map((b) => b.slug),
		languages: []
	}));
}

/** The index's audience groups, in reading-age order — the API's
 *  `Series.Audience` choices (models.py); keep the two lists in step. */
export const SERIES_AUDIENCES: readonly SeriesAudience[] = ['young_readers', 'teens', 'adults'];

/**
 * The /series index's groups: one per audience that has a series, in
 * `SERIES_AUDIENCES` order, then a group (`audience: null`) for the series no
 * one has tagged — the index's "More book series". Each group keeps the
 * list's own series order.
 */
export function groupByAudience<S extends Pick<SeriesFor, 'audience'>>(
	series: S[]
): { audience: SeriesAudience | null; series: S[] }[] {
	const known = new Set<string>(SERIES_AUDIENCES);
	const groups: { audience: SeriesAudience | null; series: S[] }[] = SERIES_AUDIENCES.map(
		(audience) => ({ audience, series: series.filter((s) => s.audience === audience) })
	);
	groups.push({ audience: null, series: series.filter((s) => !known.has(s.audience ?? '')) });
	return groups.filter((g) => g.series.length);
}

/** "Ages 9–12" / "Ages 9+", or "" for a series with no age range. */
export function seriesAges(s: Pick<SeriesFor, 'min_age' | 'max_age'>): string {
	if (s.min_age == null) return '';
	return s.max_age == null
		? m.series_ages_from({ min: s.min_age })
		: m.series_ages({ min: s.min_age, max: s.max_age });
}

// Static `m.*` references, not a built key: Paraglide type-checks and
// tree-shakes these.
const AUDIENCE_COPY: Record<SeriesAudience, { name: () => string; blurb: () => string }> = {
	young_readers: {
		name: m.series_audience_young_readers,
		blurb: m.series_audience_young_readers_desc
	},
	teens: { name: m.series_audience_teens, blurb: m.series_audience_teens_desc },
	adults: { name: m.series_audience_adults, blurb: m.series_audience_adults_desc }
};

/** An index group's heading: the audience, or "More book series" for the rest. */
export const audienceName = (a: SeriesAudience | null): string =>
	a ? AUDIENCE_COPY[a].name() : m.series_more();

/** The line under an audience heading; "" for the untagged group. */
export const audienceBlurb = (a: SeriesAudience | null): string =>
	a ? AUDIENCE_COPY[a].blurb() : '';
