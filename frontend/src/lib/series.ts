import * as m from '$lib/paraglide/messages.js';
import { UNNUMBERED_SERIES, volumeNumeral } from '$lib/coverStyles';
import type {
	BookSeriesLine,
	BookSummary,
	CoverBook,
	CoverFace,
	SeriesAudience,
	SeriesFor,
	SeriesSummary
} from '$lib/library-public';
import { toBookTile } from '$lib/library-public';
import { contentLang } from '$lib/reading';
import { i18n } from '$lib/i18n.svelte';

/**
 * The book page's one-line series label: "Book 2 of 6 in Rooted" for an
 * ordered series, "Part of The Key Teachings" for a collection.
 *
 * The numbers go through `volumeNumeral`, the call the cover's own ring makes,
 * so a Persian page says ۲ in both places rather than a ring and a sentence
 * that disagree about digits.
 *
 * "Of N" counts the published volume numbers, so while a series is still
 * coming out with its earlier volumes unwritten (Volume 2 first), N falls
 * below the book's own number; "Book 2 of 1" is false, so the line names the
 * series instead until the earlier volumes arrive.
 */
export function seriesLabel(series: BookSeriesLine, language: string): string {
	const position = UNNUMBERED_SERIES.has(series.slug)
		? null
		: volumeNumeral(series.position, language);
	if (!position || series.total < (series.position ?? 0))
		return m.book_series_member({ series: series.title });
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

/**
 * A series card's progress line, from its books' stages: "In progress" while
 * no book is finished yet (where "0 of 4 read" told a reader halfway through
 * book one they had done nothing), then "2 of 6 read". No "book N": a
 * collection has no reading order, and the card's list is this language's
 * books, which need not match the volume numbers on the covers.
 */
export function seriesCardProgressLabel(stages: BookStage[], language: string): string {
	const done = stages.filter((s) => s === 'done').length;
	return done ? seriesProgressLabel(done, stages.length, language) : m.series_in_progress();
}

/**
 * A long series name split at its spaced dash into a name and a subtitle —
 * "Daughters of the King – 30 Days with God for Girls" → "Daughters of the
 * King" over "30 Days with God for Girls" — so the card's title stays one or
 * two lines. Only a spaced en or em dash splits (the translations write one or
 * the other); a title without one comes back whole, with no subtitle.
 */
export function splitSeriesTitle(title: string): { name: string; subtitle: string } {
	const match = /\s+[–—]\s+/.exec(title);
	if (!match || match.index === 0) return { name: title, subtitle: '' };
	const subtitle = title.slice(match.index + match[0].length).trim();
	return subtitle ? { name: title.slice(0, match.index), subtitle } : { name: title, subtitle: '' };
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
export function nextInSeries<B extends Pick<BookSummary, 'slug'>>(
	books: B[],
	progressOf: (slug: string) => BookProgress
): { book: B; resume: boolean } | null {
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

/** Where a reader is with one book of a series: the card draws a segment each. */
export type BookStage = 'done' | 'reading' | 'unread';

/**
 * A reader's progress through a series, from its books' slugs: how many are
 * finished, whether any is begun at all — the card draws nothing for a series
 * the reader has never opened — and each book's stage, in reading order.
 */
export function seriesProgress(
	slugs: string[],
	progressOf: (slug: string) => BookProgress
): { done: number; total: number; started: boolean; stages: BookStage[] } {
	const stages = slugs.map((slug): BookStage => {
		const p = progressOf(slug);
		return p.finished ? 'done' : p.started ? 'reading' : 'unread';
	});
	return {
		done: stages.filter((s) => s === 'done').length,
		total: slugs.length,
		started: stages.some((s) => s !== 'unread'),
		stages
	};
}

/** One row of the index's "Continue your series": the book to open next. */
export interface SeriesToContinue<S> {
	series: S;
	slug: string;
	stages: BookStage[];
	/** When the series was last read (ms) — the order, and a mixed shelf's
	 *  key for merging these rows with others (the young-reader hubs). */
	at: number;
}

/**
 * The series a reader is partway through — a book begun, not every book
 * finished — each with the book to open next (`nextInSeries`), most recently
 * read first, at most `limit`. `lastRead` is a book's last-read time (0 for
 * never), so the series touched last leads.
 */
export function seriesToContinue<S extends Pick<SeriesSummary, 'books'>>(
	series: S[],
	progressOf: (slug: string) => BookProgress,
	lastRead: (slug: string) => number,
	limit = 3
): SeriesToContinue<S>[] {
	const rows: SeriesToContinue<S>[] = [];
	for (const s of series) {
		const slugs = s.books ?? [];
		const { started, stages } = seriesProgress(slugs, progressOf);
		if (!started) continue;
		const next = nextInSeries(slugs.map((slug) => ({ slug })), progressOf);
		if (!next) continue;
		const at = Math.max(...slugs.map(lastRead));
		rows.push({ series: s, slug: next.book.slug, stages, at });
	}
	return rows.sort((a, b) => b.at - a.at).slice(0, limit);
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
	books: (CoverFace & Pick<BookSummary, 'series'>)[]
): SeriesSummary[] {
	return groupBySeries(books, []).named.map((g) => ({
		slug: g.slug,
		title: g.title,
		description: '',
		book_count: g.books.length,
		covers: g.books.slice(0, SERIES_FAN).map(toBookTile),
		books: g.books.map((b) => b.slug),
		titles: g.books.map((b) => b.title),
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

/** Language codes a series card shows before folding the rest into "+N". */
const CARD_LANGUAGES = 5;

/**
 * A series card's language tags: the series' languages with the reader's own
 * first and the rest in code order, up to `CARD_LANGUAGES`, and the ones folded
 * into "+N" (named in its tooltip). Nothing for a series in one language — "EN" alone on an English
 * card says nothing.
 */
export function cardLanguages(
	languages: string[],
	current: string
): { shown: string[]; hidden: string[] } {
	const unique = [...new Set(languages)];
	if (unique.length < 2) return { shown: [], hidden: [] };
	const ordered = unique.sort((a, b) =>
		a === current ? -1 : b === current ? 1 : a.localeCompare(b)
	);
	return {
		shown: ordered.slice(0, CARD_LANGUAGES),
		hidden: ordered.slice(CARD_LANGUAGES)
	};
}

/**
 * Series written as a pair for different readers — the same thirty days for
 * girls and for boys — each pointing at the other. The slugs are the link, as
 * a young-reader edition's slug suffix is: nothing in the model joins them.
 */
const SERIES_COMPANIONS: Record<string, string> = {
	'daughters-of-the-king': 'sons-of-the-king',
	'sons-of-the-king': 'daughters-of-the-king'
};

/** A series' companion among `series` (the index's list), or null when it has
 *  none or the companion has no page in this language. */
export function seriesCompanion<S extends Pick<SeriesSummary, 'slug'>>(
	slug: string,
	series: S[]
): S | null {
	const other = SERIES_COMPANIONS[slug];
	return (other && series.find((s) => s.slug === other)) || null;
}

/**
 * Whether a series card says "Read in order" or "Read in any order", or
 * neither: not for a series of one book here (there's no order to speak of),
 * nor from an API behind this build that doesn't send `ordered`.
 */
export function seriesOrder(
	s: Pick<SeriesSummary, 'ordered' | 'book_count'>
): 'inOrder' | 'anyOrder' | null {
	if (s.ordered === undefined || s.book_count < 2) return null;
	return s.ordered ? 'inOrder' : 'anyOrder';
}

/** A title's tail after its last colon ("They Were Young – Book 1: Called" →
 *  "Called"), when the part before it numbers the volume (has a digit) — so
 *  "Brave for God: Book Two" keeps its title: its tail is the number. */
const NUMBERED_TAIL = /^(.*\d.*?)\s*[:：]\s*([^:：]+)$/;
/** A subtitle's lead before its colon, when it reads as a name ("Beloved: who
 *  you are…" → "Beloved"): at most three words. */
const SUBTITLE_LEAD = /^([^:：፦]{1,32})[:：፦]\s*\S/;

/**
 * A volume's own name on its series page — "Called", "Beloved", "The Black
 * Stair" — so a row and the start button stop repeating the series' name
 * ("Start with Book 1 · Called", not "Start with They Were Young – Book 1:
 * Called"). Read from the title the edition already has, in its language:
 * the tail of a numbered title, else a short lead on the subtitle, else the
 * title itself when it is not just the series' name with a number. "" when the
 * volume has no name of its own (Brave for God: Book Two) — then the number
 * says it all.
 */
export function volumeName(
	book: Pick<BookSummary, 'title' | 'subtitle'>,
	seriesTitle: string
): string {
	const tail = NUMBERED_TAIL.exec(book.title.trim());
	if (tail) return tail[2].trim();
	const lead = SUBTITLE_LEAD.exec((book.subtitle ?? '').trim())?.[1].trim();
	if (lead && lead.split(/\s+/).length <= 3) return lead;
	const title = book.title.trim();
	const name = splitSeriesTitle(seriesTitle).name.trim();
	if (!title.toLocaleLowerCase().startsWith(name.toLocaleLowerCase())) return title;
	// The series' name, then the volume's own: "Portraits of Courage – Amy
	// Carmichael", "The Golden Chain: Matthew". Only a number after it
	// or the word for one ("They Were Young – Book 1", "Brave for God: Book
	// Two") leaves the volume unnamed.
	const rest = title.slice(name.length).replace(/^[\s:：፦–—-]+/, '');
	const volume = i18n.t('originals.volume').split('%n%')[0].trim().toLocaleLowerCase();
	const numbered = /\d/.test(rest) || (!!volume && rest.toLocaleLowerCase().startsWith(volume));
	return numbered ? '' : rest;
}

/** How many books a series holds, as its head says it: "4 of 6 books" while
 *  more are planned, else "4 books" — numerals in the page's digits. */
export function seriesCountLabel(count: number, planned: number | null | undefined, language: string): string {
	const n = numeral(count, language);
	if (volumesToCome(count, planned)) {
		return i18n.t('series.booksPlanned').replace('%n%', n).replace('%total%', numeral(planned!, language));
	}
	return `${n} ${count === 1 ? i18n.t('common.bookOne') : i18n.t('common.bookMany')}`;
}

/** A number in the page's digits (`volumeNumeral`), or plain digits where the
 *  language has no numeral of its own for it. */
export function numeral(n: number, language: string): string {
	return volumeNumeral(n, language) ?? String(n);
}

/** "Book 2" in the page's digits; "" for a book with no place in an order. */
export function volumeLabel(position: number | null | undefined, language: string): string {
	return position ? i18n.t('originals.volume').replace('%n%', numeral(position, language)) : '';
}

/** The books a series still has to come: its plan less what is published. */
export function volumesToCome(count: number, planned: number | null | undefined): number {
	return planned && planned > count ? planned - count : 0;
}

/** Where a returning reader is in one volume: the chapter they last opened
 *  (its order and title, from the series row's `toc`) and how many chapters
 *  are left after it, of how many. Null with no record, or a record past the book's end. */
export function resumePoint(
	book: { toc?: string[]; chapter_count: number },
	rec: { order: number } | null
): { order: number; title: string; left: number; total: number } | null {
	const total = book.toc?.length || book.chapter_count;
	if (!rec || rec.order < 1 || rec.order > total) return null;
	return { order: rec.order, title: book.toc?.[rec.order - 1] ?? '', left: total - rec.order, total };
}

/** A daily volume's days as the reader has them: an introduction (chapter 1),
 *  then chapter n + 1 is day n. Reaching chapter c puts the reader ON day
 *  c - 1, so the days behind them are c - 2; `next` is the day to open (the
 *  one they are on, the last day once all are read). A finished volume has
 *  read every day. */
export function dailyProgress(
	furthest: number | null,
	days: number,
	finished = false
): { read: number; next: number } {
	const read = finished ? days : Math.max(0, Math.min(days, (furthest ?? 0) - 2));
	return { read, next: Math.min(days, read + 1) };
}
