import type { ScriptureBookPage, ScripturePageEntry } from '$lib/library-public';

/**
 * The /scripture hub's shape, computed from the flat page list the API sends
 * (`/api/library/scripture/pages/`): the books of the Bible grouped into their
 * canonical sections, each with its chapter pages and its most-cited verse pages,
 * plus a heat level per chapter and the most-cited chapters overall.
 *
 * Pure, so the page stays markup and this stays tested.
 */

/** A canonical section of the Bible — a run of `book_order` values (pythonbible's
 *  Book enum: Genesis = 1 … Malachi = 39, Matthew = 40 … Revelation = 66). The
 *  key is the i18n suffix (`scripture.section.<key>`) and the anchor id. */
export interface BibleSection {
	key: string;
	testament: 'old' | 'new';
	from: number;
	to: number;
}

export const BIBLE_SECTIONS: readonly BibleSection[] = [
	{ key: 'law', testament: 'old', from: 1, to: 5 },
	{ key: 'history', testament: 'old', from: 6, to: 17 },
	{ key: 'wisdom', testament: 'old', from: 18, to: 22 },
	{ key: 'majorProphets', testament: 'old', from: 23, to: 27 },
	{ key: 'minorProphets', testament: 'old', from: 28, to: 39 },
	{ key: 'gospels', testament: 'new', from: 40, to: 44 },
	{ key: 'paul', testament: 'new', from: 45, to: 57 },
	{ key: 'generalLetters', testament: 'new', from: 58, to: 65 },
	{ key: 'prophecy', testament: 'new', from: 66, to: 66 }
];

export interface IndexChapter {
	chapter: number;
	count: number;
}

export interface IndexVerse {
	chapter: number;
	verse: number;
	count: number;
}

export interface IndexBook {
	slug: string;
	title: string;
	order: number;
	chapters: IndexChapter[];
	/** The book's verse pages, most-cited first (ties in Bible order), capped. */
	topVerses: IndexVerse[];
}

export interface IndexSection extends BibleSection {
	books: IndexBook[];
}

/** How many verse pages each book surfaces under its chapters. */
export const TOP_VERSES_PER_BOOK = 5;

/**
 * Group the page list into canonical sections, dropping sections with no pages.
 * A book outside the 66 (the API filters the apocrypha today, since the bundled
 * ASV can't render it) lands in a trailing `other` section rather than vanishing.
 */
export function groupScripture(pages: ScripturePageEntry[]): IndexSection[] {
	const books = new Map<string, IndexBook & { verses: IndexVerse[] }>();
	for (const p of pages) {
		let b = books.get(p.book);
		if (!b) {
			b = {
				slug: p.book,
				title: p.book_title,
				order: p.book_order,
				chapters: [],
				topVerses: [],
				verses: []
			};
			books.set(p.book, b);
		}
		if (p.verse === null) b.chapters.push({ chapter: p.chapter, count: p.citing_count });
		else
			b.verses.push({
				chapter: p.chapter,
				verse: p.verse,
				count: p.citing_count
			});
	}

	const sections: IndexSection[] = BIBLE_SECTIONS.map((s) => ({
		...s,
		books: []
	}));
	const other: IndexSection = {
		key: 'other',
		testament: 'new',
		from: 67,
		to: Infinity,
		books: []
	};
	const sorted = [...books.values()].sort((a, b) => a.order - b.order);
	for (const { verses, ...b } of sorted) {
		// A book with verse pages but no chapter page has nothing for the chapter
		// row to hold; its verses are still reachable from search and the sitemap.
		if (!b.chapters.length) continue;
		b.chapters.sort((x, y) => x.chapter - y.chapter);
		b.topVerses = verses
			.sort((x, y) => y.count - x.count || x.chapter - y.chapter || x.verse - y.verse)
			.slice(0, TOP_VERSES_PER_BOOK);
		(sections.find((s) => b.order >= s.from && b.order <= s.to) ?? other).books.push(b);
	}
	return [...sections, other].filter((s) => s.books.length);
}

/** The number of heat levels a chapter can take, 0 (coolest) to HEAT_LEVELS - 1. */
export const HEAT_LEVELS = 5;

/**
 * A count → heat-level function, cut by rank rather than by fixed numbers, so
 * the scale stays useful as the library grows. A count's level comes from the
 * share of chapters cited LESS often than it: under half → 0, then ≥50%, ≥75%,
 * ≥90% and ≥97% → 1–4. So the top level holds at most the top 3%, equal counts
 * always share a level, and a library where most chapters are cited once (the
 * long tail this index really has) climbs one level per step instead of
 * vaulting the first count above the minimum straight to the top.
 */
export function heatScale(counts: number[]): (count: number) => number {
	if (!counts.length) return () => 0;
	const sorted = [...counts].sort((a, b) => a - b);
	const n = sorted.length;
	// How many counts are strictly below `count` (binary search, lower bound).
	const below = (count: number) => {
		let lo = 0;
		let hi = n;
		while (lo < hi) {
			const mid = (lo + hi) >> 1;
			if (sorted[mid] < count) lo = mid + 1;
			else hi = mid;
		}
		return lo;
	};
	return (count) => {
		const share = below(count) / n;
		return [0.5, 0.75, 0.9, 0.97].filter((cut) => share >= cut).length;
	};
}

export interface TopChapter {
	slug: string;
	title: string;
	chapter: number;
	count: number;
}

/** The `n` most-cited chapter pages, ties in Bible order. */
export function mostCited(pages: ScripturePageEntry[], n: number): TopChapter[] {
	return pages
		.filter((p) => p.verse === null)
		.sort((a, b) => b.citing_count - a.citing_count || a.book_order - b.book_order || a.chapter - b.chapter)
		.slice(0, n)
		.map((p) => ({
			slug: p.book,
			title: p.book_title,
			chapter: p.chapter,
			count: p.citing_count
		}));
}

/**
 * Whether the "Go to a passage" box should ask the scripture resolver at all.
 * Every reference that can have a page names a chapter, so text with no digit
 * ("grace", "John Bunyan") goes straight to the full search, skipping a round
 * trip that could only come back empty.
 */
export const mayBeReference = (q: string): boolean => /\d/.test(q);

/**
 * A count → heat-level function for ONE book's chapters (the /scripture/<book>/
 * page). heatScale is rank-based and tuned for the hub's ~600 chapters: over a
 * book's handful it can't reach the top shades (level 4 needs 34+ chapters).
 * This scales to the book's own most-cited chapter instead, so that chapter is
 * always the brightest, and the rest shade in proportion to it.
 */
export function relativeHeat(counts: number[]): (count: number) => number {
	const max = Math.max(0, ...counts);
	return (count) => (max > 0 ? Math.round(((HEAT_LEVELS - 1) * count) / max) : 0);
}

/**
 * The /scripture/<book>/ page from the page list alone — for a web build racing
 * the API's deploy (an API from before the book endpoint answers 404, and a
 * prerender 404 fails the build). Everything the list carries is here: the
 * chapter pages, the verse pages, prev/next. What only the server can count
 * (passages and works across the whole book, the works that quote it most, the
 * verse text) is left null/empty, and the page omits it. Null when the book
 * has no chapter page, which is the server's own 404 rule.
 */
export function bookFromPageList(slug: string, pages: ScripturePageEntry[]): ScriptureBookPage | null {
	const mine = pages.filter((p) => p.book === slug);
	const chapters = mine.filter((p) => p.verse === null);
	if (!chapters.length) return null;
	const books: { book: string; book_title: string }[] = [];
	for (const p of [...pages].sort((a, b) => a.book_order - b.book_order)) {
		if (p.verse === null && books.at(-1)?.book !== p.book) books.push({ book: p.book, book_title: p.book_title });
	}
	const i = books.findIndex((b) => b.book === slug);
	return {
		book: { slug, title: chapters[0].book_title, order: chapters[0].book_order },
		version: '',
		citing_count: null,
		books_count: null,
		chapters: chapters
			.map((p) => ({ chapter: p.chapter, citing_count: p.citing_count }))
			.sort((a, b) => a.chapter - b.chapter),
		verses: mine
			.filter((p) => p.verse !== null)
			.sort((a, b) => b.citing_count - a.citing_count || a.chapter - b.chapter || a.verse! - b.verse!)
			.slice(0, 8)
			.map((p) => ({ chapter: p.chapter, verse: p.verse!, citing_count: p.citing_count, text: '' })),
		top_books: [],
		prev: books[i - 1] ?? null,
		next: books[i + 1] ?? null
	};
}
