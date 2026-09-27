import { DEFAULT_HIGHLIGHT, type Mark } from './reading-schema';
import { resolveGroup, textRange } from './markAnchor';

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
	/** The words it was made on are no longer in the chapter (a repair
	 *  rewrote them): `text` is what it covered, from its stored anchor. */
	detached?: boolean;
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
	return textRange(paras[m.p] ?? '', m.s, m.e).trim();
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
	return [...byId.values()].map((stored) => {
		stored.sort((a, b) => a.p - b.p || a.s - b.s);
		// The segments where their words are now, as one unit (see markAnchor);
		// a segment whose words are gone quotes what it covered instead of
		// today's text there.
		const placed = resolveGroup(paras, stored);
		const detached = placed.every((m) => m === null);
		const first = placed.find((m): m is Mark => m !== null) ?? stored[0];
		return {
			id: stored[0].id,
			p: first.p,
			text: stored
				.map((m, i) => {
					const at = placed[i];
					if (at) return segText(paras, at);
					// Only the anchor's head is stored: say when the words ran on.
					const cut = m.q && (m.e === -1 || m.e - m.s > m.q.length) ? '…' : '';
					return (m.q ?? '').trim() + cut;
				})
				.filter(Boolean)
				.join(' … '),
			...(detached ? { detached: true } : {}),
			note: stored.find((s) => s.note)?.note,
			color: stored.find((s) => s.color)?.color ?? DEFAULT_HIGHLIGHT,
			edition
		};
	});
}
