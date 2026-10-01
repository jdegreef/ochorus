/**
 * Display typography for a quotation's text — repairs the two marks the PDF
 * extraction flattened, without touching the stored sentence.
 *
 * The stored text must stay byte-for-byte what the source paragraph says: the
 * quote seed's gate confirms each sentence appears VERBATIM in its paragraph,
 * and the slug is a hash of it. So the repair happens here, at display:
 *
 * - `--` is a typewriter em dash. The printed books set "—"; the text layer
 *   gave us two hyphens ("No man can pray -- really pray -- who does not obey").
 * - A divine name in capitals ("GOD’S love", "the LORD knows") is a small-caps
 *   name whose small caps were lost: the printed page set it as G + small
 *   capitals, and showing it shouted is the extraction's doing, not the
 *   author's. It is drawn the way the book drew it — "God" in `small-caps`.
 *   Only these names, never any all-caps word: a capitalised word can be the
 *   author's own emphasis, and that is theirs to keep.
 */

/** A stretch of quotation text, and whether it is drawn in small capitals. */
export type QuoteRun = { text: string; smallCaps: boolean };

// Whole words only, with an optional possessive in either apostrophe. Longest
// alternatives first is not needed: \b on both sides already fixes the word.
const DIVINE = /\b(GOD|LORD|CHRIST|JESUS|HOLY|GHOST|SPIRIT)(['’]S)?\b/g;

const titleCase = (word: string): string =>
  word[0] + word.slice(1).toLowerCase();

/** The text with its dashes repaired — for plain-text uses (copy, share card). */
export const plainQuote = (text: string): string => text.replace(/--/g, "—");

/** The text split into runs, the divine names marked for small capitals. */
export function quoteRuns(text: string): QuoteRun[] {
  const plain = plainQuote(text);
  const runs: QuoteRun[] = [];
  let at = 0;
  for (const m of plain.matchAll(DIVINE)) {
    if (m.index > at)
      runs.push({ text: plain.slice(at, m.index), smallCaps: false });
    runs.push({ text: titleCase(m[0]), smallCaps: true });
    at = m.index + m[0].length;
  }
  if (at < plain.length) runs.push({ text: plain.slice(at), smallCaps: false });
  return runs;
}
