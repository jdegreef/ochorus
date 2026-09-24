import * as m from "$lib/paraglide/messages.js";
import { volumeNumeral } from "$lib/coverStyles";
import type { BookSeries } from "$lib/library-public";

/**
 * The book page's one-line series label: "Book 2 of 6 in Rooted" for an
 * ordered series, "Part of The Key Teachings" for a collection.
 *
 * The numbers go through `volumeNumeral`, the call the cover's own ring makes,
 * so a Persian page says ۲ in both places rather than a ring and a sentence
 * that disagree about digits.
 */
export function seriesLabel(series: BookSeries, language: string): string {
  const position = volumeNumeral(series.position, language);
  if (!position) return m.book_series_member({ series: series.title });
  return m.book_series_volume({
    position,
    total: volumeNumeral(series.total, language) ?? String(series.total),
    series: series.title,
  });
}
