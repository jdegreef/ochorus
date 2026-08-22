import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { COVER_WIDTHS, coverSrcset, isArtCover } from "./coverArt";

/**
 * The variant widths exist in two languages and must agree.
 *
 * `scripts/build_cover_assets.py` WRITES `<cover>-320.webp` and `coverSrcset`
 * ASKS for it. There is no manifest between them — the name is a convention —
 * so if the Python tuple changes and this one doesn't, every cover asks for a
 * file nobody built. A `srcset` candidate that 404s does not fall back to
 * `src`: it renders a broken image, on every shelf at once.
 */
const COVERS_PY = join(process.cwd(), "..", "backend", "library", "covers.py");
const PY = readFileSync(COVERS_PY, "utf-8");

describe("cover variants", () => {
  it("asks for the widths the builder writes", () => {
    const match = PY.match(/^COVER_WIDTHS = \(([^)]*)\)/m);
    expect(
      match,
      "COVER_WIDTHS not found in covers.py — was it renamed?",
    ).toBeTruthy();
    const widths = match![1]
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map(Number);
    expect(COVER_WIDTHS).toEqual(widths);
  });

  it("offers density descriptors, never a width it cannot promise", () => {
    // The builder never upscales, so `godliness-640.webp` is really 424px —
    // a `640w` claim would be false and the browser selects on it.
    const set = coverSrcset("/covers/godliness.jpg");
    expect(set).toBe(
      "/covers/godliness-320.webp 1x, /covers/godliness-640.webp 2x",
    );
    expect(set).not.toMatch(/\d+w\b/); // no width descriptors, only 1x/2x
  });

  it("offers nothing for a cover with no variants", () => {
    expect(coverSrcset("/covers/all-of-grace.svg")).toBe("");
    expect(coverSrcset("")).toBe("");
    expect(coverSrcset(null)).toBe("");
  });

  it("knows a painting from a finished cover", () => {
    expect(isArtCover("/covers/art/waiting-on-god.jpg")).toBe(true);
    expect(isArtCover("/covers/humility-2.jpg")).toBe(false);
    expect(isArtCover(null)).toBe(false);
  });
});
