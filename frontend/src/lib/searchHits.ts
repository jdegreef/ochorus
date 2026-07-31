import type { Segment } from './marks.svelte';

/**
 * Where a search query occurs in a chapter's text.
 *
 * Arriving from a search result used to drop the reader at the top of the
 * chapter, leaving them to re-find the sentence they were shown. This computes
 * the character ranges to highlight — as plain offsets into each top-level
 * block's text, which is the same coordinate system the highlight/notes feature
 * already uses (`reading-schema.Segment`).
 *
 * Deliberately pure string work: it never touches the DOM. The wrapping is done
 * by `rangeMarks.renderMarks`, which already splits text nodes rather than
 * rewriting HTML — chapter bodies are server-sanitised and the reader trusts
 * them, so a string replace here would be a way to reintroduce exactly what the
 * sanitiser exists to prevent.
 *
 * **What it does not do.** The server matches with Postgres full-text search:
 * stemmed, so "praying" finds "prayer", and accent-folded depending on config.
 * This matches literal words, case-insensitively. So a result can legitimately
 * open with nothing highlighted — the reader simply lands at the top, as they
 * did before. Guessing at stems here would highlight the wrong words, which is
 * worse than highlighting none.
 */

/** Ignore one-character words: they match everywhere and highlight nothing useful. */
const MIN_WORD = 2;

/** A ceiling on wrapped ranges, so a short query can't split thousands of nodes. */
const MAX_HITS = 200;

/**
 * The words to look for, from a raw search query.
 *
 * Strips the websearch operators the API accepts (`"phrase"`, `OR`, leading `-`)
 * rather than searching for them literally — a reader who typed `prayer -healing`
 * means the word prayer, not the punctuation.
 */
export function queryWords(query: string): string[] {
	return (query ?? '')
		.replace(/["']/g, ' ')
		.split(/\s+/)
		.map((w) => w.replace(/^-+/, '').trim())
		.filter((w) => w.length >= MIN_WORD && w.toUpperCase() !== 'OR')
		.map((w) => w.toLowerCase());
}

/**
 * Character ranges of `query`'s words within each block's text.
 *
 * `blocks` are the top-level blocks' `textContent`, in document order — `p` in
 * the returned segments indexes that array, matching how marks are stored.
 * Overlapping matches (from two words sharing a prefix) are merged so nothing
 * is wrapped twice.
 */
export function findQueryHits(blocks: string[], query: string): Segment[] {
	const words = queryWords(query);
	if (!words.length) return [];

	const out: Segment[] = [];
	for (let p = 0; p < blocks.length && out.length < MAX_HITS; p++) {
		const haystack = (blocks[p] ?? '').toLowerCase();
		if (!haystack) continue;
		const ranges: [number, number][] = [];
		for (const w of words) {
			let from = haystack.indexOf(w);
			while (from !== -1) {
				ranges.push([from, from + w.length]);
				from = haystack.indexOf(w, from + w.length);
			}
		}
		for (const [s, e] of merge(ranges)) {
			out.push({ p, s, e });
			if (out.length >= MAX_HITS) break;
		}
	}
	return out;
}

/** Sort and coalesce overlapping/adjacent ranges. */
function merge(ranges: [number, number][]): [number, number][] {
	if (ranges.length < 2) return ranges;
	const sorted = [...ranges].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
	const out: [number, number][] = [sorted[0]];
	for (const [s, e] of sorted.slice(1)) {
		const last = out[out.length - 1];
		if (s <= last[1]) last[1] = Math.max(last[1], e);
		else out.push([s, e]);
	}
	return out;
}
