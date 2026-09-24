import { describe, expect, it } from "vitest";
import { seriesLabel } from "./series";
import type { BookSeries } from "./library-public";

const rooted: BookSeries = {
  slug: "rooted",
  title: "Rooted",
  position: 2,
  total: 6,
  previous: null,
  next: null,
};

describe("seriesLabel", () => {
  it("numbers an ordered series", () => {
    expect(seriesLabel(rooted, "en")).toBe("Book 2 of 6 in Rooted");
  });

  it("names a collection without a number", () => {
    expect(
      seriesLabel(
        { ...rooted, title: "The Key Teachings", position: null, total: 4 },
        "en",
      ),
    ).toBe("Part of The Key Teachings");
  });

  it("sets the numbers in the edition's own digits, as the cover ring does", () => {
    expect(seriesLabel(rooted, "fa")).toBe("Book ۲ of ۶ in Rooted");
  });
});
