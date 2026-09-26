import type { Mark } from './reading-schema';

/**
 * Keeping a highlight on its words when the chapter's text is repaired.
 *
 * A mark is offsets (block `p`, characters `s`..`e`) plus `q`, the start of
 * the text it covered when made. Where `q` still sits at the offsets the mark
 * is used as is; where it doesn't, it is looked for in the same block and its
 * neighbours, nearest first; where it is nowhere, the mark is detached rather
 * than painted over other words. Stored offsets are never rewritten — they are
 * the mark's identity in the server's merge — so this runs per render.
 */

/** How much of a highlight's text is kept to find it again — the whole of a
 *  typical highlight, so an edit anywhere in it is noticed, capped so a long
 *  one doesn't bloat every sync. */
export const QUOTE_MAX = 200;

/** An anchor shorter than this (a word or two) is too common to look for
 *  beyond its own block: another 'grace' two paragraphs on is not it. */
const SHORT_ANCHOR = 12;

/** Blocks either side of the stored one searched, nearest first — a split or
 *  merged paragraph shifts indices by a few, not dozens. */
const SEARCH_ORDER = [0, -1, 1, -2, 2, -3, 3];

/** The text of [s, e) in a block (`e === -1` = to the end of the block). */
export function textRange(text: string, s: number, e: number): string {
	return text.slice(s, e === -1 ? undefined : e);
}

/** The anchor text for a segment of block text `text`. */
export function quoteOf(text: string, s: number, e: number): string {
	return textRange(text, s, e).slice(0, QUOTE_MAX);
}

/**
 * Where a mark sits in the chapter as it is now: the mark itself when its text
 * is still at its offsets (or it predates anchors and can't be checked), a
 * copy at the words' new place when they moved, or null when they are gone.
 */
export function resolveMark(paras: string[], m: Mark): Mark | null {
	if (!m.q || paras[m.p]?.startsWith(m.q, m.s)) return m;
	for (const d of m.q.length < SHORT_ANCHOR ? [0] : SEARCH_ORDER) {
		const text = paras[m.p + d];
		if (text === undefined) continue;
		let best = -1;
		for (let at = text.indexOf(m.q); at !== -1; at = text.indexOf(m.q, at + 1)) {
			if (best === -1 || Math.abs(at - m.s) < Math.abs(best - m.s)) best = at;
		}
		if (best !== -1) return { ...m, p: m.p + d, s: best, e: m.e === -1 ? -1 : best + (m.e - m.s) };
	}
	return null;
}

/** The marks that can still be placed, each where its words are now. */
export function placeMarks(paras: string[], list: Mark[]): Mark[] {
	return list.map((m) => resolveMark(paras, m)).filter((m): m is Mark => m !== null);
}
