/**
 * A Bible book's contents as a grid of numbered chips (1 … 150 for Psalms)
 * rather than a 150-row list.
 *
 * `build_owb_book` titles each chapter "<Book> <n>" ("Genesis 3", "Psalm 23")
 * between an "Introduction" and a "Conclusion", so a chip's number is the
 * Bible's own chapter number read off the title — NOT the row's `order`, which
 * is one ahead of it because the introduction is order 1. A chapter whose title
 * ends in no number (the introduction, the conclusion) keeps its title as the
 * chip's label.
 */
import { BIBLE_SERIES } from '$lib/bible';

/** The Bible chapter number a chapter title ends in ("Psalm 23" → 23), or null. */
export function chapterNumber(title: string | null | undefined): number | null {
	const m = title?.match(/\s(\d{1,3})$/);
	return m ? Number(m[1]) : null;
}

/**
 * Whether a book's contents draw as the chip grid: a book of the Bible (the
 * `the-bible` series). Asked of the book rather than of its chapter count, so a
 * long classic keeps its titled list — its chapter titles ARE its contents,
 * where a Bible book's are only "<Book> <n>".
 */
export const chapterGridFor = (book: { series?: { slug: string } | null }) =>
	book.series?.slug === BIBLE_SERIES;
