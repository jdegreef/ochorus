// "Chapter of the day" — a chapter of the Bible for every reader to read today,
// shown beside the day's verse on the home page's Today card.
//
// Deterministic, like the sermon of the day: everyone reads the same chapter on
// the same local date, and it turns over at local midnight with no manual step
// — so a reader can talk about "today's chapter" with someone else who reads
// here. Picked CLIENT-SIDE by the caller ($lib/todayPicks), because the pages
// are prerendered.
//
// The rotation walks the Bible hub's "Where to start" path chapter by chapter —
// Mark, John, Genesis, Psalms, Romans: 253 days — and then begins again. One
// chapter a day through the books a first reader is pointed to, in that order,
// rather than a random draw, so a reader who comes back daily reads them whole.

import { localDayNumber } from '$lib/dailyArticles';
import { bookChapterPath } from '$lib/reading-schema';
import { bibleChapterOrder, chapterLabel } from '$lib/bible';

/** The path, as (Bible book slug, its place in the canon, chapters). A
 *  book's chapter `n` is reader chapter `n + 1`: `build_owb_book` sets an
 *  introduction first. The chapter is named by `chapterLabel`, in the
 *  reader's language. */
export const DAILY_CHAPTER_PATH: readonly (readonly [slug: string, position: number, chapters: number])[] = [
	['gospel-of-mark', 41, 16],
	['gospel-of-john', 43, 21],
	['genesis', 1, 50],
	['psalms', 19, 150],
	['romans', 45, 16]
];

/** Days in one turn of the path (253). */
export const DAILY_CHAPTER_CYCLE = DAILY_CHAPTER_PATH.reduce((n, [, , c]) => n + c, 0);

export interface DailyChapter {
	/** The Bible book's slug. */
	slug: string;
	/** The reader chapter's `order` (the Bible chapter + 1). */
	order: number;
	/** As the chapter is titled in the reader's language: "Mark 4", «Salmo 23». */
	title: string;
	/** Its path (unlocalized). */
	href: string;
}

/** The chapter for the local date of `date`, titled in `lang`. */
export function pickDailyChapter(date: Date, lang: string): DailyChapter {
	let day = localDayNumber(date) % DAILY_CHAPTER_CYCLE;
	for (const [slug, position, chapters] of DAILY_CHAPTER_PATH) {
		if (day < chapters) {
			const order = bibleChapterOrder(day + 1);
			const title = chapterLabel(position, day + 1, lang)!;
			return { slug, order, title, href: bookChapterPath(slug, order, false) };
		}
		day -= chapters;
	}
	throw new Error('unreachable: day is within the cycle');
}
