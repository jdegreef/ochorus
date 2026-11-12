import { describe, expect, it } from "vitest";

import { SIZE } from "./quoteCard";
import {
  layoutPostcard,
  postmarkLines,
  stampGround,
  type TextMeasure,
} from "./postcardCard";

/** A fake canvas: every glyph half an em wide at the current font's px size. */
function fakeCtx(): TextMeasure {
  let font = "16px serif";
  return {
    get font() {
      return font;
    },
    set font(f: string) {
      font = f;
    },
    measureText: (t: string) => {
      const px = Number(/(\d+)px/.exec(font)?.[1] ?? 16);
      return { width: t.length * px * 0.5 } as TextMetrics;
    },
  } as TextMeasure;
}

const base = {
  quote: "Grace upon grace.",
  author: "C. H. Spurgeon",
  source: "All of Grace, Chapter 1",
};

describe("postcard layout: text fitting", () => {
  it("sets a short quote large and a long one smaller, both inside the message half", () => {
    const short = layoutPostcard(fakeCtx(), base);
    const long = layoutPostcard(fakeCtx(), {
      ...base,
      quote: "word ".repeat(80),
    });
    const size = (l: typeof short) => Number(/(\d+)px/.exec(l.quote.font)![1]);
    expect(size(short)).toBeGreaterThan(size(long));
    for (const l of [short, long]) {
      const { box, lines, lineHeight, top } = l.quote;
      // Never wider than its half, never past the divider.
      for (const line of lines)
        expect(line.length * size(l) * 0.5).toBeLessThanOrEqual(box.w);
      expect(box.x + box.w).toBeLessThan(l.divider.x);
      expect(top).toBeGreaterThanOrEqual(box.y);
      expect(top + lines.length * lineHeight).toBeLessThanOrEqual(
        box.y + box.h + 0.01,
      );
    }
  });

  it("keeps every word of a quote it can fit", () => {
    const l = layoutPostcard(fakeCtx(), {
      ...base,
      quote: "I had rather bless the soul of the poorest crossing-sweeper",
    });
    // A line may end on a hyphen it broke after; nothing else is lost.
    expect(l.quote.lines.join(" ").replace(/- /g, "-")).toBe(
      "I had rather bless the soul of the poorest crossing-sweeper",
    );
  });

  /** The fake, with kana, kanji and the ellipsis a full em wide — as a CJK
   *  face draws them. */
  function wideCtx(): TextMeasure {
    const ctx = fakeCtx();
    const measure = ctx.measureText;
    ctx.measureText = (t: string) => {
      const px = Number(/(\d+)px/.exec(ctx.font)?.[1] ?? 16);
      const wide = [...t].filter(
        (c) => c === "…" || c.codePointAt(0)! > 0x2e80,
      ).length;
      return { width: measure(t).width + wide * px * 0.5 } as TextMetrics;
    };
    return ctx;
  }
  const inside = (l: ReturnType<typeof layoutPostcard>, ctx: TextMeasure) => {
    const { box, lines, lineHeight, top, font } = l.quote;
    expect(top + lines.length * lineHeight).toBeLessThanOrEqual(
      box.y + box.h + 0.01,
    );
    ctx.font = font;
    for (const line of lines)
      expect(ctx.measureText(line).width, line).toBeLessThanOrEqual(box.w);
  };

  it("cuts a quote that overflows even at the smallest size, rather than run into the author", () => {
    // Kana and kanji are a full em each and wrap per character, so a
    // 300-character Japanese quote needs ~20 lines at 26px — more than the
    // message half holds.
    for (const quote of [
      "神の恵みは尽きることがない。".repeat(30),
      // Puts a 、 just before where the ellipsis must go once a character
      // is dropped to make room for it.
      "あ".repeat(8) + "主は、わが牧者なり、".repeat(30),
    ]) {
      const ctx = wideCtx();
      const l = layoutPostcard(ctx, { ...base, language: "ja", quote });
      inside(l, ctx);
      const last = l.quote.lines.at(-1)!;
      expect(last.endsWith("…")).toBe(true);
      expect(last, last).not.toMatch(/[、。，]…$/);
    }
  });

  it("breaks a dash chain at its dashes and keeps it large", () => {
    const ctx = fakeCtx();
    const l = layoutPostcard(ctx, {
      ...base,
      quote: "Love—joy—peace—patience—kindness—goodness is the fruit",
    });
    inside(l, ctx);
    expect(Number(/(\d+)px/.exec(l.quote.font)![1])).toBeGreaterThan(40);
    for (const line of l.quote.lines)
      expect(line).toMatch(/^(?:[A-Za-z]+[—\s]?)+$/); // no word split mid-letter
  });

  it("shrinks for a long word, and breaks a run no size can fit, never past the divider", () => {
    const word = layoutPostcard(fakeCtx(), {
      ...base,
      quote: "Bless the crossing-sweeper",
    });
    expect(word.quote.lines.join(" ")).toContain("crossing-");
    // Hangul written without spaces: one 300-character run.
    const ctx = fakeCtx();
    const run = layoutPostcard(ctx, {
      ...base,
      language: "ko",
      quote: "하나님의은혜는다함이없도다".repeat(30),
    });
    expect(run.quote.lines.length).toBeGreaterThan(1);
    inside(run, ctx);
  });

  it("lets the words after a broken run share its last line", () => {
    const ctx = fakeCtx();
    const l = layoutPostcard(ctx, {
      ...base,
      quote: `Bless the ${"x".repeat(60)} and the poor`,
    });
    inside(l, ctx);
    expect(l.quote.lines.at(-1)).toMatch(/x and the poor$/);
  });

  it("clamps a long source to two lines with an ellipsis", () => {
    const l = layoutPostcard(fakeCtx(), {
      ...base,
      source: "A very long source title ".repeat(10),
    });
    expect(l.attribution.source).toHaveLength(2);
    expect(l.attribution.source[1].endsWith("…")).toBe(true);
  });

  it("sets the classic face, italic for Latin and upright for other scripts", () => {
    expect(layoutPostcard(fakeCtx(), base).quote.font).toMatch(
      /^italic 600 \d+px 'EB Garamond Variable'/,
    );
    for (const language of ["ar", "hi", "ko", "am", "ja"]) {
      const font = layoutPostcard(fakeCtx(), { ...base, language }).quote.font;
      expect(font, language).toMatch(/^400 \d+px 'EB Garamond Variable'/);
    }
  });
});

describe("postcard postmark", () => {
  it("is omitted when there is no city and no year", () => {
    expect(postmarkLines(undefined, undefined)).toBeNull();
    expect(postmarkLines("  ", null)).toBeNull();
    expect(layoutPostcard(fakeCtx(), base).postmark).toBeNull();
  });

  it("prints only what it has", () => {
    expect(postmarkLines(null, 1886)).toEqual(["· 1886 ·"]);
    expect(postmarkLines("London", null)).toEqual(["LONDON"]);
    expect(postmarkLines("London", 1886)).toEqual(["LONDON", "· 1886 ·"]);
    expect(
      layoutPostcard(fakeCtx(), { ...base, year: 1886 }).postmark?.lines,
    ).toEqual(["· 1886 ·"]);
  });

  it("rejects a year that is not one", () => {
    expect(postmarkLines(null, 0)).toBeNull();
    expect(postmarkLines(null, 1886.5)).toBeNull();
  });

  it("upper-cases a city in its own language, and prints the year plainly", () => {
    expect(postmarkLines("istanbul", 1886, "tr")).toEqual([
      "İSTANBUL",
      "· 1886 ·",
    ]);
    expect(postmarkLines(null, 1886, "ar")).toEqual(["· 1886 ·"]);
  });
});

describe("postcard stamp", () => {
  it("wears the cover colour, darkened only as far as white type needs", () => {
    expect(stampGround("#1f3a5f")).toBe("#1f3a5f");
    expect(stampGround("#f0d070")).not.toBe("#f0d070");
  });

  it("falls back to a postal red for no or malformed colour", () => {
    expect(stampGround(undefined)).toBe(stampGround(""));
    expect(stampGround("red; x")).toBe(stampGround(null));
  });
});

describe("postcard RTL", () => {
  const ltr = layoutPostcard(fakeCtx(), {
    ...base,
    language: "en",
    year: 1886,
  });
  const rtl = layoutPostcard(fakeCtx(), {
    ...base,
    language: "ar",
    year: 1886,
  });

  it("mirrors only Arabic", () => {
    expect(ltr.rtl).toBe(false);
    expect(rtl.rtl).toBe(true);
    expect(layoutPostcard(fakeCtx(), { ...base, language: "hi" }).rtl).toBe(
      false,
    );
  });

  it("puts the message on the right and the stamp on the left", () => {
    expect(rtl.quote.box.x).toBeGreaterThan(rtl.divider.x);
    expect(rtl.stamp.x + rtl.stamp.w).toBeLessThan(rtl.divider.x);
    expect(rtl.quote.box.x).toBe(SIZE - ltr.quote.box.x - ltr.quote.box.w);
    expect(rtl.stamp.x).toBe(SIZE - ltr.stamp.x - ltr.stamp.w);
    expect(rtl.postmark!.cx).toBe(SIZE - ltr.postmark!.cx);
    expect(rtl.footer.x).toBe(SIZE - ltr.footer.x - ltr.footer.w);
  });

  it("starts the attribution at the right edge and keeps ranges ordered", () => {
    expect(rtl.attribution.x).toBe(SIZE - ltr.attribution.x);
    expect(rtl.rules.x1).toBeLessThan(rtl.rules.x2);
    expect(rtl.cancel.x1).toBeLessThan(rtl.cancel.x2);
    expect(rtl.rules.x2).toBeLessThan(rtl.divider.x);
  });
});
