import { DEFAULT_HIGHLIGHT, type Mark } from './reading-schema';

/**
 * Resolving stored marks back to the text they highlight.
 *
 * A mark anchors at (p = top-level block index, s/e = character range within that
 * block's text content); the block text isn't stored, so quoting a highlight means
 * re-splitting the chapter's HTML into the same blocks the reader indexed against
 * and slicing the range. Shared by the notebook (whole-library) and the in-reader
 * notes drawer (one book) so the two can't drift.
 */

/** One highlight/note group, ready to render: its joined text, optional note and
 *  colour, plus the paragraph it starts on (for a `?p=` jump) and its edition. */
export type Highlight = {
	id: string;
	p: number;
	text: string;
	note?: string;
	color: string;
	edition: string;
};

/** Split a chapter's cleaned HTML into its top-level blocks' text — the same
 *  blocks the reader indexes marks against (p = block, s/e = chars in it). */
export function paragraphs(bodyHtml: string): string[] {
	const div = document.createElement('div');
	div.innerHTML = bodyHtml;
	return [...div.children].map((el) => el.textContent ?? '');
}

/** The text one mark segment covers (`e === -1` = to the end of the block). */
export function segText(paras: string[], m: Mark): string {
	const tx = paras[m.p] ?? '';
	return tx.slice(m.s, m.e === -1 ? undefined : m.e).trim();
}

/**
 * Group a chapter's mark segments into renderable highlights. One selection can
 * span several blocks sharing an id; those join (in reading order) into one
 * highlight, and the note — which lives on the first segment — rides along.
 */
export function groupMarks(paras: string[], ms: Mark[], edition: string): Highlight[] {
	const byId = new Map<string, Mark[]>();
	for (const m of ms) {
		const arr = byId.get(m.id) ?? [];
		arr.push(m);
		byId.set(m.id, arr);
	}
	return [...byId.values()].map((segs) => {
		segs.sort((a, b) => a.p - b.p || a.s - b.s);
		return {
			id: segs[0].id,
			p: segs[0].p,
			text: segs
				.map((s) => segText(paras, s))
				.filter(Boolean)
				.join(' … '),
			note: segs.find((s) => s.note)?.note,
			color: segs.find((s) => s.color)?.color ?? DEFAULT_HIGHLIGHT,
			edition
		};
	});
}
