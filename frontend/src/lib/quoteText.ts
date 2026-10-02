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

/**
 * A paragraph split around the quotation it contains, for highlighting the
 * sentence in context. Whitespace-insensitive (the API sends the paragraph
 * with its whitespace collapsed); null when the sentence is not found, so the
 * caller shows the paragraph unmarked rather than guessing.
 */
export function splitAround(
  paragraph: string,
  quote: string,
): { before: string; match: string; after: string } | null {
  const needle = quote.split(/\s+/).filter(Boolean).join(" ");
  const at = needle ? paragraph.indexOf(needle) : -1;
  if (at < 0) return null;
  return {
    before: paragraph.slice(0, at),
    match: paragraph.slice(at, at + needle.length),
    after: paragraph.slice(at + needle.length),
  };
}

/**
 * Which of `size` items is "today's": days since the epoch in the reader's
 * own calendar, so the pick turns over at their midnight and walks the whole
 * list before repeating. 0 for an empty list.
 */
export function dayIndex(now: Date, size: number): number {
  if (size <= 0) return 0;
  const day = Math.floor(
    (now.getTime() - now.getTimezoneOffset() * 60_000) / 86_400_000,
  );
  return ((day % size) + size) % size;
}
