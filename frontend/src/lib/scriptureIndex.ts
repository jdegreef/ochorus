import type { ScripturePageEntry } from "$lib/library-public";

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
  testament: "old" | "new";
  from: number;
  to: number;
}

export const BIBLE_SECTIONS: readonly BibleSection[] = [
  { key: "law", testament: "old", from: 1, to: 5 },
  { key: "history", testament: "old", from: 6, to: 17 },
  { key: "wisdom", testament: "old", from: 18, to: 22 },
  { key: "majorProphets", testament: "old", from: 23, to: 27 },
  { key: "minorProphets", testament: "old", from: 28, to: 39 },
  { key: "gospels", testament: "new", from: 40, to: 44 },
  { key: "paul", testament: "new", from: 45, to: 57 },
  { key: "generalLetters", testament: "new", from: 58, to: 65 },
  { key: "prophecy", testament: "new", from: 66, to: 66 },
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
        verses: [],
      };
      books.set(p.book, b);
    }
    if (p.verse === null)
      b.chapters.push({ chapter: p.chapter, count: p.citing_count });
    else
      b.verses.push({
        chapter: p.chapter,
        verse: p.verse,
        count: p.citing_count,
      });
  }

  const sections: IndexSection[] = BIBLE_SECTIONS.map((s) => ({
    ...s,
    books: [],
  }));
  const other: IndexSection = {
    key: "other",
    testament: "new",
    from: 67,
    to: Infinity,
    books: [],
  };
  const sorted = [...books.values()].sort((a, b) => a.order - b.order);
  for (const { verses, ...b } of sorted) {
    // A book with verse pages but no chapter page has nothing for the chapter
    // row to hold; its verses are still reachable from search and the sitemap.
    if (!b.chapters.length) continue;
    b.chapters.sort((x, y) => x.chapter - y.chapter);
    b.topVerses = verses
      .sort(
        (x, y) =>
          y.count - x.count || x.chapter - y.chapter || x.verse - y.verse,
      )
      .slice(0, TOP_VERSES_PER_BOOK);
    (
      sections.find((s) => b.order >= s.from && b.order <= s.to) ?? other
    ).books.push(b);
  }
  return [...sections, other].filter((s) => s.books.length);
}

/** The number of heat levels a chapter can take, 0 (coolest) to HEAT_LEVELS - 1. */
export const HEAT_LEVELS = 5;

/**
 * A count → heat-level function, cut by rank rather than by fixed numbers, so
 * the scale stays useful as the library grows: the bottom half of chapters are
 * level 0, then the next quarter, the next 15%, the next 7%, and the top 3%.
 * Equal counts always share a level (the cut is the count AT that rank).
 */
export function heatScale(counts: number[]): (count: number) => number {
  if (!counts.length) return () => 0;
  const sorted = [...counts].sort((a, b) => a - b);
  const at = (q: number) =>
    sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))];
  const cuts = [0.5, 0.75, 0.9, 0.97].map(at);
  return (count) => {
    let level = 0;
    // A cut equal to the minimum would lift every chapter off level 0, so a
    // level is earned only by exceeding the lowest count too.
    for (const c of cuts) if (count >= c && count > sorted[0]) level++;
    return level;
  };
}

export interface TopChapter {
  slug: string;
  title: string;
  chapter: number;
  count: number;
}

/** The `n` most-cited chapter pages, ties in Bible order. */
export function mostCited(
  pages: ScripturePageEntry[],
  n: number,
): TopChapter[] {
  return pages
    .filter((p) => p.verse === null)
    .sort(
      (a, b) =>
        b.citing_count - a.citing_count ||
        a.book_order - b.book_order ||
        a.chapter - b.chapter,
    )
    .slice(0, n)
    .map((p) => ({
      slug: p.book,
      title: p.book_title,
      chapter: p.chapter,
      count: p.citing_count,
    }));
}
