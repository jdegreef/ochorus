import { describe, it, expect } from "vitest";
import type { ScripturePageEntry } from "$lib/library-public";
import {
  BIBLE_SECTIONS,
  groupScripture,
  heatScale,
  mostCited,
  TOP_VERSES_PER_BOOK,
} from "./scriptureIndex";

const page = (
  book: string,
  order: number,
  chapter: number,
  count: number,
  verse: number | null = null,
): ScripturePageEntry => ({
  book,
  book_title: book[0].toUpperCase() + book.slice(1),
  book_order: order,
  chapter,
  verse,
  citing_count: count,
});

describe("BIBLE_SECTIONS", () => {
  it("covers books 1–66 once each, in order", () => {
    const seen: number[] = [];
    for (const s of BIBLE_SECTIONS)
      for (let o = s.from; o <= s.to; o++) seen.push(o);
    expect(seen).toEqual(Array.from({ length: 66 }, (_, i) => i + 1));
  });
  it("splits the testaments at Matthew", () => {
    expect(BIBLE_SECTIONS.filter((s) => s.testament === "old").at(-1)!.to).toBe(
      39,
    );
    expect(BIBLE_SECTIONS.find((s) => s.testament === "new")!.from).toBe(40);
  });
});

describe("groupScripture", () => {
  it("groups books into their sections in canonical order, dropping empty sections", () => {
    const out = groupScripture([
      page("romans", 45, 8, 30),
      page("genesis", 1, 3, 5),
      page("exodus", 2, 20, 4),
      page("psalms", 19, 23, 9),
    ]);
    expect(out.map((s) => s.key)).toEqual(["law", "wisdom", "paul"]);
    expect(out[0].books.map((b) => b.slug)).toEqual(["genesis", "exodus"]);
  });

  it("sorts chapters and keeps verse pages out of the chapter row", () => {
    const [law] = groupScripture([
      page("genesis", 1, 22, 5),
      page("genesis", 1, 3, 5),
      page("genesis", 1, 3, 4, 15),
    ]);
    expect(law.books[0].chapters).toEqual([
      { chapter: 3, count: 5 },
      { chapter: 22, count: 5 },
    ]);
  });

  it("surfaces the most-cited verse pages, ties in Bible order, capped", () => {
    const verses = [
      page("romans", 45, 8, 9, 28),
      page("romans", 45, 5, 4, 8),
      page("romans", 45, 8, 4, 1),
      page("romans", 45, 12, 2, 1),
      page("romans", 45, 3, 3, 23),
      page("romans", 45, 6, 3, 23),
      page("romans", 45, 1, 2, 16),
    ];
    const [paul] = groupScripture([page("romans", 45, 8, 30), ...verses]);
    const top = paul.books[0].topVerses;
    expect(top).toHaveLength(TOP_VERSES_PER_BOOK);
    expect(top.map((v) => `${v.chapter}:${v.verse}`)).toEqual([
      "8:28",
      "5:8",
      "8:1",
      "3:23",
      "6:23",
    ]);
  });

  it("keeps a book outside the 66 in a trailing section", () => {
    const out = groupScripture([
      page("tobit", 67, 4, 3),
      page("genesis", 1, 1, 3),
    ]);
    expect(out.map((s) => s.key)).toEqual(["law", "other"]);
  });

  it("skips a book that has verse pages but no chapter page", () => {
    expect(groupScripture([page("jude", 65, 1, 3, 24)])).toEqual([]);
  });
});

describe("heatScale", () => {
  it("puts the bottom half at 0 and the very top at the highest level", () => {
    const counts = Array.from({ length: 100 }, (_, i) => i + 1);
    const level = heatScale(counts);
    expect(level(1)).toBe(0);
    expect(level(50)).toBe(0);
    expect(level(51)).toBe(1);
    expect(level(76)).toBe(2);
    expect(level(91)).toBe(3);
    expect(level(100)).toBe(4);
  });
  it("gives equal counts the same level, and a flat library no heat", () => {
    const level = heatScale([3, 3, 3, 3]);
    expect(level(3)).toBe(0);
  });
  it("is never above the top level or below 0", () => {
    const level = heatScale([1, 2, 2, 2, 2, 9]);
    for (const c of [0, 1, 2, 9, 50]) {
      expect(level(c)).toBeGreaterThanOrEqual(0);
      expect(level(c)).toBeLessThanOrEqual(4);
    }
  });
  it("copes with no counts", () => {
    expect(heatScale([])(10)).toBe(0);
  });
});

describe("mostCited", () => {
  it("ranks chapter pages only, ties in Bible order", () => {
    const top = mostCited(
      [
        page("john", 43, 3, 40),
        page("romans", 45, 8, 40),
        page("romans", 45, 8, 99, 28),
        page("genesis", 1, 3, 12),
      ],
      2,
    );
    expect(top.map((t) => `${t.slug} ${t.chapter}`)).toEqual([
      "john 3",
      "romans 8",
    ]);
  });
});
