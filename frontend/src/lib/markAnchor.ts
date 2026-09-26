import type { Mark } from './reading-schema';

/**
 * Keeping a highlight on its words when the text under it changes.
 *
 * A mark is stored as offsets — block `p`, characters `s`..`e` — and nothing
 * else, so any content repair that shifts a chapter's text (an English QA fix,
 * a split paragraph, a repaired quotation mark) silently moved every highlight
 * after it onto the wrong words, and the notebook quoted the wrong sentence.
 *
 * So a mark also carries `q`, the text it covered when it was made (the first
 * QUOTE_MAX characters of it). Where that text still sits at the stored
 * offsets the mark is used as is; where it doesn't, the words are looked for in
 * the same block and its neighbours, nearest first; and where they are nowhere
 * to be found the mark is detached — not painted over whatever now occupies
 * its old place. The stored offsets are never rewritten: they are the mark's
 * identity on the server, and the resolution is cheap enough to redo per render.
 */

/** How much of a highlight's text is kept to find it again. Enough to be
 *  unambiguous in a chapter, small enough not to bloat every sync. */
export const QUOTE_MAX = 200;

/** How many blocks either side of the stored one a moved highlight is looked
 *  for in — a split or merged paragraph shifts indices by a few, not dozens. */
const SEARCH_RADIUS = 3;

/** The anchor text for a segment of block text `text`. */
export function quoteOf(text: string, s: number, e: number): string {
	return text.slice(s, e === -1 ? undefined : e).slice(0, QUOTE_MAX);
}

/**
 * Where a mark sits in the chapter as it is now: the mark itself when its text
 * is still at its offsets (or it predates quotes and can't be checked), a copy
 * at the words' new place when they moved, or null when they are gone.
 */
export function resolveMark(paras: string[], m: Mark): Mark | null {
	const q = m.q;
	if (!q) return m;
	if (paras[m.p]?.startsWith(q, m.s)) return m;
	const length = m.e === -1 ? -1 : m.e - m.s;
	const order = [0];
	for (let d = 1; d <= SEARCH_RADIUS; d++) order.push(-d, d);
	for (const d of order) {
		const text = paras[m.p + d];
		if (text === undefined) continue;
		let best = -1;
		for (let at = text.indexOf(q); at !== -1; at = text.indexOf(q, at + 1)) {
			if (best === -1 || Math.abs(at - m.s) < Math.abs(best - m.s)) best = at;
		}
		if (best !== -1) {
			return { ...m, p: m.p + d, s: best, e: length === -1 ? -1 : best + length };
		}
	}
	return null;
}
