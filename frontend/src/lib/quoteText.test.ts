import { describe, expect, it } from "vitest";
import { dayIndex, quoteRuns, splitAround } from "./quoteText";

describe("quoteRuns", () => {
  it("draws a capitalised divine name, possessive included, in small caps", () => {
    expect(
      quoteRuns("Our love to GOD is secured by GOD’S love to us."),
    ).toEqual([
      { text: "Our love to ", smallCaps: false },
      { text: "God", smallCaps: true },
      { text: " is secured by ", smallCaps: false },
      { text: "God’s", smallCaps: true },
      { text: " love to us.", smallCaps: false },
    ]);
  });

  it("handles a straight-apostrophe possessive and a name that opens the line", () => {
    expect(quoteRuns("GOD'S overflow")).toEqual([
      { text: "God's", smallCaps: true },
      { text: " overflow", smallCaps: false },
    ]);
  });

  it("marks each word of a two-word name", () => {
    expect(
      quoteRuns("the HOLY GHOST")
        .filter((r) => r.smallCaps)
        .map((r) => r.text),
    ).toEqual(["Holy", "Ghost"]);
  });

  it("keeps other capitals and mixed-case names exactly as stored", () => {
    expect(quoteRuns("God is NOT mocked; GODLY fear.")).toEqual([
      { text: "God is NOT mocked; GODLY fear.", smallCaps: false },
    ]);
  });
});

describe("splitAround", () => {
  it("splits a paragraph around the sentence it contains", () => {
    expect(
      splitAround("Before it. The line itself. After it.", "The line itself."),
    ).toEqual({
      before: "Before it. ",
      match: "The line itself.",
      after: " After it.",
    });
  });

  it("ignores whitespace differences in the quotation", () => {
    expect(splitAround("a b c", " b\n")?.match).toBe("b");
  });

  it("returns null when the sentence is not there", () => {
    expect(splitAround("Nothing here.", "Elsewhere.")).toBeNull();
    expect(splitAround("Anything.", "  ")).toBeNull();
  });
});

describe("dayIndex", () => {
  it("steps by one each day and wraps", () => {
    const d = new Date(2026, 9, 2, 12);
    const next = new Date(2026, 9, 3, 12);
    const n = 7;
    expect(dayIndex(next, n)).toBe((dayIndex(d, n) + 1) % n);
  });

  it("holds for the whole of a local day", () => {
    expect(dayIndex(new Date(2026, 9, 2, 0, 1), 50)).toBe(
      dayIndex(new Date(2026, 9, 2, 23, 59), 50),
    );
  });

  it("is 0 for an empty list", () => {
    expect(dayIndex(new Date(), 0)).toBe(0);
  });
});
