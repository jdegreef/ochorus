/**
 * Measuring how fast THIS reader reads, from what the reader already reports:
 * the paragraph at the top of the screen, sampled whenever it changes.
 *
 * Two consecutive samples say "the top moved from paragraph 4 to 7 in 51 s",
 * and the words of paragraphs 4–6 over 51 s is a pace. Only forward moves
 * count, only within a plausible window — a gap under 1.5 s is a flick, over
 * five minutes is a coffee, a pace under 40 or over 1200 wpm is a skim or a
 * scroll to find something — because one bad sample at 6000 wpm would poison
 * every estimate in the app for a while.
 */

export interface PaceSample {
	/** Top-visible paragraph index. */
	p: number;
	/** Clock ms. */
	at: number;
}

export const MIN_GAP_MS = 1500;
export const MAX_GAP_MS = 5 * 60 * 1000;
export const MIN_WPM = 40;
export const MAX_WPM = 1200;

/** Words in a run of text — close enough to how the server counts word_count
 *  (it splits on whitespace after replacing tags with spaces, so a tag inside
 *  a word counts two there and one here; a hair, and cosmetic). */
export function wordCount(text: string): number {
	return (text.match(/\S+/g) ?? []).length;
}

/** Per-paragraph word counts of a rendered chapter body's top-level blocks. */
export function paragraphWordCounts(children: ArrayLike<Element>): number[] {
	return Array.from(children, (el) => wordCount(el.textContent ?? ''));
}

/**
 * The reading that happened between two samples, as words over ms — or null
 * when the move was not a plausible stretch of reading (see above).
 */
export function paceDelta(
	prev: PaceSample,
	next: PaceSample,
	paragraphWords: number[]
): { words: number; ms: number } | null {
	if (next.p <= prev.p) return null;
	const ms = next.at - prev.at;
	if (ms < MIN_GAP_MS || ms > MAX_GAP_MS) return null;
	let words = 0;
	for (let i = prev.p; i < next.p; i++) words += paragraphWords[i] ?? 0;
	if (words <= 0) return null;
	const wpm = (words / ms) * 60_000;
	if (wpm < MIN_WPM || wpm > MAX_WPM) return null;
	return { words, ms };
}
