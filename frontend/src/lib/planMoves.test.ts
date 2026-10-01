import { describe, expect, it } from "vitest";
import { PLAN_MOVES, applyPlanMoves, movedDone } from "./planMoves";

const move = PLAN_MOVES["the-key-teachings-four-teachers"][0];

describe("the Four Teachers plan move", () => {
  it("maps all 88 old days into 86 new ones, each old day once", () => {
    expect(move.sources).toHaveLength(86);
    expect(move.books).toHaveLength(86);
    expect(move.sources.flat().sort((a, b) => a - b)).toEqual(
      Array.from({ length: 88 }, (_, i) => i + 1),
    );
  });

  it("keeps a finished plan finished, new chapters included", () => {
    const all = Array.from({ length: 88 }, (_, i) => i + 1);
    expect(movedDone(move, all)).toHaveLength(86);
  });

  it("marks a merged day only when every day it replaces was done", () => {
    expect(movedDone(move, [1, 2, 3, 4])).toEqual([1, 2, 3]); // old 4+5 -> new 4
    expect(movedDone(move, [1, 2, 3, 4, 5])).toEqual([1, 2, 3, 4]);
  });

  it("marks a brand-new day read-past only inside the same book", () => {
    // new day 32 (Edwards) sits between old 34 (new 31) and old 35 (new 33)
    expect(movedDone(move, [34, 35])).toEqual([31, 32, 33]);
    expect(movedDone(move, [34])).toEqual([31]);
  });

  it("moves a device store to the new slug once and drops the old one", () => {
    const store: Record<string, { startedAt: number; done: number[] }> = {
      "the-key-teachings-four-teachers": { startedAt: 5, done: [1, 2] },
      other: { startedAt: 1, done: [3] },
    };
    expect(applyPlanMoves(store)).toEqual(["key-teachings-four-teachers"]);
    expect(store["the-key-teachings-four-teachers"]).toBeUndefined();
    expect(store["key-teachings-four-teachers"]).toEqual({
      startedAt: 5,
      done: [1, 2],
    });
    expect(store.other).toEqual({ startedAt: 1, done: [3] });
    expect(applyPlanMoves(store)).toEqual([]);
  });
});

describe("the young-reader series plan moves", () => {
  const range = (from: number, to: number) =>
    Array.from({ length: to - from + 1 }, (_, i) => from + i);
  type Store = Record<string, { startedAt: number; done: number[] }>;

  it('puts a per-book day N on that book’s "Day N" chapter of the series plan', () => {
    // Book 2's Day 1 is chapter 2 of the plan's second book: 32 + 2.
    const [m] = PLAN_MOVES["rooted-book-2-30-days"];
    expect(m.to).toBe("rooted-three-months-books-1-3");
    expect(m.sources).toHaveLength(96);
    expect(movedDone(m, [1, 2, 30])).toEqual([34, 35, 63]);
    // The Introduction and Conclusion had no day of their own: they start unread.
    expect(movedDone(m, range(1, 30))).toEqual(range(34, 63));
  });

  it("sends each series to its one plan (Rooted to its two halves)", () => {
    const to = (slug: string) => PLAN_MOVES[slug].map((m) => m.to);
    expect(to("rooted-book-3-30-days")).toEqual([
      "rooted-three-months-books-1-3",
    ]);
    expect(to("rooted-book-4-30-days")).toEqual([
      "rooted-three-months-books-4-6",
    ]);
    expect(to("daughters-of-the-king-book-3-30-days")).toEqual([
      "daughters-of-the-king-three-months",
    ]);
    expect(to("sons-of-the-king-book-1-30-days")).toEqual([
      "sons-of-the-king-three-months",
    ]);
    expect(movedDone(PLAN_MOVES["rooted-book-4-30-days"][0], [1])).toEqual([2]);
  });

  it("splits the six-month plan across the halves the reader reached", () => {
    const store: Store = {
      "rooted-six-months-with-god": { startedAt: 7, done: [1, 2, 96, 97, 98] },
      "rooted-three-months-books-4-6": { startedAt: 3, done: [10] },
    };
    expect(applyPlanMoves(store).sort()).toEqual([
      "rooted-three-months-books-1-3",
      "rooted-three-months-books-4-6",
    ]);
    expect(store["rooted-six-months-with-god"]).toBeUndefined();
    expect(store["rooted-three-months-books-1-3"]).toEqual({
      startedAt: 7,
      done: [1, 2, 96],
    });
    expect(store["rooted-three-months-books-4-6"]).toEqual({
      startedAt: 3,
      done: [1, 2, 10],
    });

    const early: Store = {
      "rooted-six-months-with-god": { startedAt: 1, done: [] },
    };
    expect(applyPlanMoves(early)).toEqual(["rooted-three-months-books-1-3"]);
    expect(early).toEqual({
      "rooted-three-months-books-1-3": { startedAt: 1, done: [] },
    });
  });

  it("unions several retired plans into the one plan they became", () => {
    const store: Store = {
      "daughters-of-the-king-book-1-30-days": { startedAt: 5, done: [1] },
      "daughters-of-the-king-book-2-30-days": { startedAt: 9, done: [1] },
    };
    expect(applyPlanMoves(store)).toEqual([
      "daughters-of-the-king-three-months",
    ]);
    expect(store).toEqual({
      "daughters-of-the-king-three-months": { startedAt: 5, done: [2, 34] },
    });
  });
});
