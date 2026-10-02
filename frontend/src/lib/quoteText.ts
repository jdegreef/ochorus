/**
 * Display typography for a quotation's text, without touching the stored
 * sentence — which must stay byte-for-byte what its source paragraph says (the
 * quote seed's gate confirms each sentence appears VERBATIM there).
 *
 * (Typewriter dashes were repaired here too until the stored text itself was
 * fixed — `library/dashes.py`, run on every deploy.)
 *
 * - A divine name in capitals ("GOD’S love", "the LORD knows") is a small-caps
 *   name whose small caps were lost: the printed page set it as G + small
 *   capitals, and showing it shouted is the extraction's doing, not the
 *   author's. It is drawn the way the book drew it — "God" in `small-caps`.
 *   Only these names, never any all-caps word: a capitalised word can be the
 *   author's own emphasis, and that is theirs to keep.
 */

/** A stretch of quotation text, and whether it is drawn in small capitals. */
export type QuoteRun = { text: string; smallCaps: boolean };

// Whole words only, with an optional possessive in either apostrophe. A
// narrower cousin of the backend's `english_audit.SMALLCAP_WORDS`: only names
// a book set in small caps, not every word that list watches for.
const DIVINE = /\b(GOD|LORD|CHRIST|JESUS|HOLY|GHOST|SPIRIT)(['’]S)?\b/g;

const titleCase = (word: string): string =>
  word[0] + word.slice(1).toLowerCase();

/** The text split into runs, the divine names marked for small capitals. */
export function quoteRuns(text: string): QuoteRun[] {
  const runs: QuoteRun[] = [];
  let at = 0;
  for (const m of text.matchAll(DIVINE)) {
    if (m.index > at)
      runs.push({ text: text.slice(at, m.index), smallCaps: false });
    runs.push({ text: titleCase(m[0]), smallCaps: true });
    at = m.index + m[0].length;
  }
  if (at < text.length) runs.push({ text: text.slice(at), smallCaps: false });
  return runs;
}
