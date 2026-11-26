import type { SermonSummary } from '$lib/library-public';
import { BIBLE_CHAPTER_COUNTS } from '$lib/reading-schema';
import { CANON } from '$lib/sermonCanon';

/**
 * "Sermons on <book of the Bible>" — one crawlable page per book that enough
 * sermons preach from (/sermons/on/<book>/), grouped by chapter. It is the
 * sermons shelf's book facet given an address: the same `scripture_book_order`
 * (backend `scripture.book_of`, a sermon's own text only), so the page, the
 * shelf's "Browse by Scripture" cell and the Bible book's "All N sermons" link
 * count the same sermons.
 *
 * A book's slug is its `CANON` name, slugified ("1 Corinthians" →
 * `1-corinthians`, "Song of Songs" → `song-of-songs`): the name a searcher
 * types, not the library's Bible-book slug (`gospel-of-john`).
 *
 * Pure, so the route stays markup and this stays tested.
 */

/** Fewer sermons than this and a book gets no page: two cards are a thin page,
 *  and the shelf's facet already serves them. The route 404s below it, and
 *  every link to the page checks it, so the crawler never meets a dead one. */
export const SERMONS_ON_FLOOR = 3;

const slugify = (name: string) => name.toLowerCase().replace(/\s+/g, '-');

const SLUGS: readonly string[] = CANON.map(([name]) => slugify(name));

/** The page's slug for the book at canonical `position` (Genesis = 1). */
export const sermonsOnSlug = (position: number): string | null => SLUGS[position - 1] ?? null;

/** The canonical position of a page slug, or null for an unknown one. */
export function sermonsOnPosition(slug: string): number | null {
	const i = SLUGS.indexOf(slug);
	return i < 0 ? null : i + 1;
}

/** The page's path (unlocalized, trailing slash: it prerenders to a directory). */
export function sermonsOnPath(position: number): string | null {
	const slug = sermonsOnSlug(position);
	return slug ? `/sermons/on/${slug}/` : null;
}

/** The library's Bible-book slug at `position` (`gospel-of-john`), for links
 *  to the text itself. */
export const bibleBookSlug = (position: number): string | null =>
	Object.keys(BIBLE_CHAPTER_COUNTS)[position - 1] ?? null;

/** Sermons per book, by canonical position. */
export function sermonCountsByBook(sermons: Pick<SermonSummary, 'scripture_book_order'>[]) {
	const m = new Map<number, number>();
	for (const s of sermons) {
		const p = s.scripture_book_order;
		if (p != null && sermonsOnSlug(p)) m.set(p, (m.get(p) ?? 0) + 1);
	}
	return m;
}

/** The positions with a page in this list of sermons, in canonical order. */
export function sermonsOnBooks(sermons: Pick<SermonSummary, 'scripture_book_order'>[]): number[] {
	return [...sermonCountsByBook(sermons)]
		.filter(([, n]) => n >= SERMONS_ON_FLOOR)
		.map(([p]) => p)
		.sort((a, b) => a - b);
}

/** The path for a book when it has a page, else null — what a link checks. */
export const sermonsOnHref = (position: number | null | undefined, count: number): string | null =>
	position != null && count >= SERMONS_ON_FLOOR ? sermonsOnPath(position) : null;

/**
 * The chapter and first verse a ref opens on, after its book name:
 * "1 Corinthians 9:26-27" → [9, 26], "Psalm 23" → [23, 0]. Null when it names
 * no chapter. The book's own leading digit ("1 John") is skipped.
 */
export function refChapter(ref: string): [chapter: number, verse: number] | null {
	const m = /^\s*(?:[1-3]\s*)?[^\d]+?\s*(\d+)(?:\s*[:.]\s*(\d+))?/.exec(ref);
	return m ? [Number(m[1]), m[2] ? Number(m[2]) : 0] : null;
}

export interface ChapterGroup {
	/** Null for sermons on the book as a whole (no chapter in the ref). */
	chapter: number | null;
	sermons: SermonSummary[];
}

/**
 * The sermons on the book at `position`, grouped by chapter in Bible order —
 * within a chapter by first verse, then title; the chapterless last.
 */
export function sermonsOnGroups(sermons: SermonSummary[], position: number): ChapterGroup[] {
	const keyed = sermons
		.filter((s) => s.scripture_book_order === position)
		.map((s) => ({ s, at: refChapter(s.scripture_ref) }));
	keyed.sort(
		(a, b) =>
			(a.at?.[0] ?? Infinity) - (b.at?.[0] ?? Infinity) ||
			(a.at?.[1] ?? 0) - (b.at?.[1] ?? 0) ||
			a.s.title.localeCompare(b.s.title)
	);
	const groups: ChapterGroup[] = [];
	for (const { s, at } of keyed) {
		const chapter = at?.[0] ?? null;
		const last = groups.at(-1);
		if (last && last.chapter === chapter) last.sermons.push(s);
		else groups.push({ chapter, sermons: [s] });
	}
	return groups;
}
