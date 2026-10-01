import { describe, expect, it } from "vitest";
import { plainQuote, quoteRuns } from "./quoteText";

describe("plainQuote", () => {
  it("sets a typewriter double hyphen as an em dash", () => {
    expect(
      plainQuote("No man can pray -- really pray -- who does not obey."),
    ).toBe("No man can pray — really pray — who does not obey.");
  });

  it("leaves capitals alone — plain text has no small caps to fall back to", () => {
    expect(plainQuote("Our love to GOD")).toBe("Our love to GOD");
  });
});

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

  it("repairs dashes in the runs too", () => {
    expect(quoteRuns("a -- b")).toEqual([{ text: "a — b", smallCaps: false }]);
  });
});
