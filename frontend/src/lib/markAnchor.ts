import type { Mark } from './reading-schema';

/**
 * Keeping a highlight on its words when the chapter's text is repaired.
 *
 * A mark is offsets (block `p`, characters `s`..`e`) plus `q`, the start of
 * the text it covered when made. Where `q` still sits at the offsets the mark
 * is used as is; where it doesn't, it is looked for in the same block and its
 * neighbours, nearest first; where it is nowhere, the mark is detached rather
 * than painted over other words. This runs per render and never rewrites the
 * stored offsets: the server does that, once, in the deploy that repaired the
 * text (backend/reading/anchor.py — same rules, keep the two in step), and its
 * merge matches a mark by (id, lang, q) as well as offsets, so a device still
 * holding the old ones doesn't duplicate it.
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

/** The occurrence of `q` in `text` nearest offset `near`, or -1. */
function nearest(text: string, q: string, near: number): number {
	let best = -1;
	for (let at = text.indexOf(q); at !== -1; at = text.indexOf(q, at + 1)) {
		if (best === -1 || Math.abs(at - near) < Math.abs(best - near)) best = at;
	}
	return best;
}

/**
 * Segment `m` looked for around block `at` (its own block shifted by its
 * group's displacement), within blocks `lo`..`hi`, nearest its old offset
 * (so in place when its anchor still sits there). A short anchor is too
 * common to search the neighbours for: it is tried at `at` and then, if that
 * is not where it was, in its own block.
 */
function find(paras: string[], m: Mark, at: number, lo = 0, hi = Infinity): Mark | null {
	if (!m.q) return m;
	const tries =
		m.q.length < SHORT_ANCHOR ? [...new Set([at, m.p])] : SEARCH_ORDER.map((d) => at + d);
	for (const p of tries) {
		if (p < lo || p > hi || paras[p] === undefined) continue;
		const s = nearest(paras[p], m.q, m.s);
		if (s === -1) continue;
		return p === m.p && s === m.s ? m : { ...m, p, s, e: m.e === -1 ? -1 : s + (m.e - m.s) };
	}
	return null;
}

/**
 * Where one highlight's segments sit in the chapter now, as a unit — one
 * selection across several blocks is stored as a segment per block sharing an
 * id, and resolving each alone let them come apart: a short tail ("And so")
 * is only looked for in its own block, so it stayed behind (or landed on
 * other words) when the paragraphs before it shifted.
 *
 * The longest anchor is placed first and fixes the group's displacement; the
 * segments after it are then looked for in reading order, and those before
 * it in reverse, each where the displacement of its neighbour nearer the lead
 * puts it and never past that neighbour (a split or merged paragraph inside
 * the run shifts the rest). A segment that can't be found is null; the others
 * still place. Returned in `segs`'s order.
 */
export function resolveGroup(paras: string[], segs: Mark[]): (Mark | null)[] {
	const order = segs
		.map((_, i) => i)
		.sort((a, b) => segs[a].p - segs[b].p || segs[a].s - segs[b].s);
	const len = (k: number) => segs[order[k]].q?.length ?? 0;
	let li = 0;
	for (let k = 1; k < order.length; k++) if (len(k) > len(li)) li = k;
	const lead = segs[order[li]];
	const placed = lead.q ? find(paras, lead, lead.p) : null;
	const out: (Mark | null)[] = new Array(segs.length).fill(null);
	const walk = (start: number, step: 1 | -1) => {
		let shift = placed ? placed.p - lead.p : 0;
		let bound = placed ? placed.p : 0;
		for (let k = start; k >= 0 && k < order.length; k += step) {
			const seg = segs[order[k]];
			const at = seg.p + shift;
			const m = step === 1 ? find(paras, seg, at, bound) : find(paras, seg, at, 0, bound);
			out[order[k]] = m;
			// An unanchored segment can't be checked, so it says nothing about
			// where the run went.
			if (m && seg.q) {
				shift = m.p - seg.p;
				bound = m.p;
			}
		}
	};
	if (placed) {
		out[order[li]] = placed;
		walk(li + 1, 1);
		walk(li - 1, -1);
	} else {
		walk(0, 1);
	}
	return out;
}

/**
 * Where a single mark sits in the chapter as it is now: the mark itself when
 * its text is still at its offsets (or it predates anchors and can't be
 * checked), a copy at the words' new place when they moved, or null when they
 * are gone.
 */
export function resolveMark(paras: string[], m: Mark): Mark | null {
	return find(paras, m, m.p);
}

/** The marks that can still be placed, each where its words are now — a
 *  multi-block highlight's segments resolved together (see resolveGroup). */
export function placeMarks(paras: string[], list: Mark[]): Mark[] {
	// Nearly always nothing has moved: skip the grouping on every render.
	if (list.every((m) => !m.q || paras[m.p]?.startsWith(m.q, m.s))) return list.slice();
	// Keyed like the server's remap (reading/anchor.py): a group is its id in
	// one edition.
	const groups = new Map<string, Mark[]>();
	for (const m of list) {
		const key = `${m.id}\u0000${m.lang ?? ''}`;
		const arr = groups.get(key) ?? [];
		arr.push(m);
		groups.set(key, arr);
	}
	return [...groups.values()]
		.flatMap((segs) => resolveGroup(paras, segs))
		.filter((m): m is Mark => m !== null);
}
