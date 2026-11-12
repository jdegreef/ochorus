import { describe, expect, it } from "vitest";
import {
  chapterBars,
  chapterRangeText,
  compactWords,
  edgeSlot,
  lengthBuckets,
} from "./chapterLengths";

const DATA = {
  edges: [
    150, 500, 1000, 2000, 3000, 4000, 5000, 6000, 8000, 10000, 12000, 16000,
  ],
  counts: [90, 1683, 2504, 3123, 1502, 817, 539, 306, 387, 126, 74, 44, 15],
  tiny_max: 150,
  giant_min: 8000,
};

describe("compactWords", () => {
  it("abbreviates thousands", () => {
    expect(compactWords(150)).toBe("150");
    expect(compactWords(1000)).toBe("1k");
    expect(compactWords(1500)).toBe("1.5k");
    expect(compactWords(16000)).toBe("16k");
  });
});

describe("lengthBuckets", () => {
  const b = lengthBuckets(DATA);

  it("labels the open ends and the ranges between edges", () => {
    expect(b).toHaveLength(13);
    expect(b[0]).toMatchObject({
      label: "<150",
      range: "Under 150 words",
      count: 90,
    });
    expect(b[2]).toMatchObject({ label: "500–1k", range: "500–999 words" });
    expect(b[12]).toMatchObject({
      label: "16k+",
      range: "Over 16,000 words",
      count: 15,
    });
  });

  it("gives an exact range either side of the giant line (8,000 itself is not giant)", () => {
    expect(b[8].range).toBe("6,000–8,000 words");
    expect(b[9].range).toBe("8,001–10,000 words");
  });

  it("flags exactly the buckets past either threshold", () => {
    expect(b.map((x) => x.flag)).toEqual([
      "tiny",
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      "giant",
      "giant",
      "giant",
      "giant",
    ]);
    const giant = b
      .filter((x) => x.flag === "giant")
      .reduce((n, x) => n + x.count, 0);
    expect(giant).toBe(259);
  });

  it("follows the thresholds the API sends, not a hard-coded pair", () => {
    const moved = lengthBuckets({ ...DATA, tiny_max: 500, giant_min: 10000 });
    expect(moved.map((x) => x.flag).slice(0, 3)).toEqual([
      "tiny",
      "tiny",
      null,
    ]);
    expect(moved[9].flag).toBeNull(); // 8–10k is now under the line
    expect(moved[10].flag).toBe("giant");
  });
});

describe("edgeSlot", () => {
  it("puts a threshold line between the buckets either side of its edge", () => {
    expect(edgeSlot(DATA, 150)).toBe(1);
    expect(edgeSlot(DATA, 8000)).toBe(9);
    expect(edgeSlot(DATA, 7)).toBe(-1);
  });
});

describe("chapterBars", () => {
  const min = (w: number) => Math.max(1, Math.round(w / 200));

  it("scales each chapter to the longest, with a floor for a short one", () => {
    expect(chapterBars([1000, 4000, 2000, 50], min)).toEqual({
      heights: [25, 100, 50, 8],
      shortest: 1,
      longest: 20,
    });
  });

  it("leaves an empty chapter at zero and out of the range", () => {
    expect(chapterBars([0, 400, 800, 1600], min)?.heights).toEqual([
      0, 25, 50, 100,
    ]);
    expect(chapterBars([0, 400, 800, 1600], min)?.shortest).toBe(2);
  });

  it("draws nothing for a tiny or a very long book", () => {
    expect(chapterBars([500, 900], min)).toBeNull();
    expect(chapterBars([0, 0, 500, 900], min)).toBeNull();
    expect(chapterBars(Array(61).fill(500), min)).toBeNull();
    expect(chapterBars(Array(60).fill(500), min)).not.toBeNull();
  });
});

describe("chapterRangeText", () => {
  it("fills a range, and collapses one that is a single figure", () => {
    expect(
      chapterRangeText("%min%–%max% min a chapter", {
        shortest: 3,
        longest: 9,
      }),
    ).toBe("3–9 min a chapter");
    expect(
      chapterRangeText("%min%–%max% min a chapter", {
        shortest: 5,
        longest: 5,
      }),
    ).toBe("5 min a chapter");
    expect(
      chapterRangeText("%min% à %max% min par chapitre", {
        shortest: 5,
        longest: 5,
      }),
    ).toBe("5 min par chapitre");
  });
});
