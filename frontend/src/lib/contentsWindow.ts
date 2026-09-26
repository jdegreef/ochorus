/**
 * Which chapters a long table of contents shows before "Show all".
 *
 * A 36-chapter book listed in full pushed the Q&A and "More like this" a long
 * scroll down the book page. Collapsed, the list keeps what a reader needs:
 * the first chapter, the last, and the reader's place with two chapters either
 * side of it — or, with no saved place (a first visit, and the prerendered
 * page), the opening chapters.
 *
 * Returns the chapter orders to show, or `null` for "show them all" (a list
 * short enough not to collapse). A gap that would hide a single chapter is
 * filled instead: "⋯ 1 chapter" takes a row to save a row.
 */
export const CONTENTS_COLLAPSE_AT = 12;
const AROUND = 2;
const OPENING = 5;

export function contentsWindow(orders: number[], current: number | null): Set<number> | null {
	const n = orders.length;
	if (n <= CONTENTS_COLLAPSE_AT) return null;

	const at = current == null ? -1 : orders.indexOf(current);
	const keep = new Set<number>([0, n - 1]);
	if (at >= 0) {
		for (let i = at - AROUND; i <= at + AROUND; i++) if (i >= 0 && i < n) keep.add(i);
	} else {
		for (let i = 0; i < OPENING; i++) keep.add(i);
	}
	// Fill one-chapter gaps.
	for (let i = 1; i < n - 1; i++) {
		if (!keep.has(i) && keep.has(i - 1) && keep.has(i + 1)) keep.add(i);
	}
	return new Set([...keep].map((i) => orders[i]));
}
