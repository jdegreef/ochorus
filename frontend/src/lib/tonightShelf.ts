import { pickByDay } from '$lib/dailyPicks';
import { editionKind } from '$lib/edition';
import { DEFAULT_WPM } from '$lib/readingPace.svelte';
import type { SermonFaceSource } from '$lib/sermonArt';
import {
	toCoverBook,
	type AuthorBio,
	type BookSummary,
	type CoverBook,
	type SermonSummary
} from '$lib/library-public';

/**
 * "Tonight, under 20 minutes" (idea #27): whole works a reader can FINISH in
 * one evening sitting — a short book, a single sermon, a writer's biography —
 * shown on the home page in the evening only.
 *
 * Two halves, both pure:
 *
 * - `tonightPool` runs at BUILD time inside the home snapshot (`homeShelves`),
 *   from the lists the snapshot already fetches — no request of its own. It
 *   keeps what is under 20 min at the default pace in THIS language (the lists are
 *   per-language rows; there is no English fallback, so a locale with few short
 *   works simply has a small pool), and picks a varied handful, kinds
 *   interleaved.
 * - `tonightShelf` runs in the BROWSER at mount: the reader's local clock
 *   decides whether it is evening, and the reader's own pace (`readingMinutes`)
 *   re-checks each work's time — a slower reader's "18 min" sermon may be 24 —
 *   so a card never promises a sitting the "N min" under it contradicts. Fewer
 *   than `TONIGHT_MIN_ITEMS` left → no shelf: two cards under "Tonight" read
 *   as a gap, not an offer.
 */

/** The promise in the shelf's title: "in under N minutes". */
export const TONIGHT_MAX_MINUTES = 20;
/** Whether a card's printed minutes keep that promise — strictly under, so a
 *  "20 min read" never sits beneath "under 20 minutes". One rule for both
 *  halves, so the pool and the shelf cannot disagree at the default pace. */
const underTheLimit = (minutes: number) => minutes < TONIGHT_MAX_MINUTES;
/** Below this many works the shelf hides rather than look half-empty. */
export const TONIGHT_MIN_ITEMS = 4;
/** How many cards the shelf shows: one row of six on a desktop, a rail on a phone. */
export const TONIGHT_SHOWN = 6;
/** Per kind in the snapshot — slack for the browser's pace re-check. */
const PER_KIND = 4;
/** The evening window in local hours: from 19:00, through midnight, until 04:00. */
export const EVENING_FROM = 19;
export const EVENING_UNTIL = 4;

/** A sermon as the shelf draws it (`sermonCoverFace` + its time). */
export type TonightSermon = SermonFaceSource & Pick<SermonSummary, 'word_count'>;

/** A writer whose long biography is a one-sitting read. */
export interface TonightWriter {
	slug: string;
	name: string;
	language: string;
	birth_year: number | null;
	death_year: number | null;
	word_count: number;
}

export type TonightItem =
	| { kind: 'book'; book: CoverBook }
	| { kind: 'sermon'; sermon: TonightSermon }
	| { kind: 'bio'; writer: TonightWriter };

/** The words a work's sitting is measured from. */
export function wordsOf(item: TonightItem): number {
	if (item.kind === 'book') return item.book.word_count ?? 0;
	if (item.kind === 'sermon') return item.sermon.word_count;
	return item.writer.word_count;
}

/** A stable key per work (a writer and their book may share a slug). */
export const tonightKey = (item: TonightItem): string =>
	item.kind === 'book'
		? `book:${item.book.slug}`
		: item.kind === 'sermon'
			? `sermon:${item.sermon.slug}`
			: `bio:${item.writer.slug}`;

/** Whether `now` (the reader's local clock) is in the evening window. */
export function isEvening(now: Date): boolean {
	const h = now.getHours();
	return h >= EVENING_FROM || h < EVENING_UNTIL;
}

/**
 * The snapshot's pool for `language`: up to `PER_KIND` books, sermons and
 * biographies of under `TONIGHT_MAX_MINUTES` at the default pace, by
 * different writers where the library allows, interleaved book · sermon ·
 * biography so the first cards already show the range. Full texts before
 * young-reader editions (`<base>-children` / `-teens`): in most languages the
 * short books are mostly those, and an evening shelf of children's editions
 * would misread who it is for — they still fill a thin language.
 */
export function tonightPool(
	lists: {
		books: BookSummary[];
		sermons: SermonSummary[];
		authors: AuthorBio[];
	},
	language: string,
	day: number
): TonightItem[] {
	// The minutes the card will print at the default pace (`readingMinutes`'
	// rounding), kept strictly under the title's "under N minutes".
	const fits = (words: number | null | undefined) =>
		!!words && words > 0 && underTheLimit(Math.max(1, Math.round(words / DEFAULT_WPM)));

	const short = lists.books.filter((b) => b.language === language && fits(b.word_count));
	const full = short.filter((b) => !editionKind(b.slug));
	const books = pickByDay(full, PER_KIND, day, (b) => b.author.slug);
	if (books.length < PER_KIND) {
		// Never a young-reader edition beside its own full text (the slug
		// convention is the link): the shelf would offer one work twice.
		const picked = new Set(books.map((b) => b.slug));
		const young = short.filter((b) => {
			const kind = editionKind(b.slug);
			return kind && !picked.has(b.slug.slice(0, -(kind.length + 1)));
		});
		books.push(
			...pickByDay(
				young,
				PER_KIND - books.length,
				day,
				(b) => b.author.slug,
				books.map((b) => b.author.slug)
			)
		);
	}
	const bookAuthors = books.map((b) => b.author.slug);

	const sermons = pickByDay(
		lists.sermons.filter((s) => s.language === language && fits(s.word_count)),
		PER_KIND,
		day,
		(s) => s.author.slug,
		bookAuthors
	);

	const writers = pickByDay(
		// A count > 0 IS a long bio in this language (0 without one).
		lists.authors.filter((a) => fits(a.bio_word_count)),
		PER_KIND,
		day,
		(a) => a.slug,
		[...bookAuthors, ...sermons.map((s) => s.author.slug)]
	);

	const kinds: TonightItem[][] = [
		books.map((b) => ({ kind: 'book', book: toCoverBook(b) })),
		sermons.map((s) => ({
			kind: 'sermon',
			sermon: {
				slug: s.slug,
				language: s.language,
				title: s.title,
				scripture_ref: s.scripture_ref,
				word_count: s.word_count,
				author: { slug: s.author.slug, name: s.author.name, birth_year: s.author.birth_year }
			}
		})),
		writers.map((a) => ({
			kind: 'bio',
			writer: {
				slug: a.slug,
				name: a.name,
				language,
				birth_year: a.birth_year,
				death_year: a.death_year,
				word_count: a.bio_word_count ?? 0
			}
		}))
	];
	const pool: TonightItem[] = [];
	for (let i = 0; i < PER_KIND; i++) {
		for (const list of kinds) if (list[i]) pool.push(list[i]);
	}
	return pool;
}

/**
 * What the shelf shows at `now`, given the reader's minutes for a word count:
 * nothing outside the evening, nothing when fewer than `TONIGHT_MIN_ITEMS`
 * works fit the reader's own pace, else the first `TONIGHT_SHOWN` that do.
 */
export function tonightShelf(
	pool: readonly TonightItem[],
	now: Date,
	minutesOf: (words: number) => number
): TonightItem[] {
	if (!isEvening(now)) return [];
	const fit = pool.filter((item) => {
		const words = wordsOf(item);
		return words > 0 && underTheLimit(minutesOf(words));
	});
	return fit.length < TONIGHT_MIN_ITEMS ? [] : fit.slice(0, TONIGHT_SHOWN);
}
