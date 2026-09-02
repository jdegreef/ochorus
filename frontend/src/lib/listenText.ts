/**
 * What a footnote marker is, and how to remove one — shared by every surface
 * that has to show a reader's prose without the eye-only bits in it.
 *
 * Chapter prose carries reference markers that are on the page for the eye, not
 * for anything downstream of it: a `<sup>4</sup>` after a sentence, or an inline
 * `[2]`. The listen engine would voice them ("…grace **four**"); the shareable
 * quote card would bake them into the PNG ("grace;[4]"); the search index would
 * disagree with both. So the *definition* of a marker lives here, in one place,
 * and each surface removes markers in the way its own coordinate system allows.
 *
 * The two kinds of marker are owned in two different places, because they are
 * not the same kind of thing:
 *
 *  - `<sup>` footnote residue is stripped at IMPORT, not here. In this corpus a
 *    `<sup>` is only ever a footnote marker (numbered or empty) pointing at a
 *    note that is gone, so the backend removes the lone ones from the stored
 *    body outright — junk for the eye as much as the ear
 *    (`library/corrections.py` `strip_footnote_markers`). Dropping `<sup>` below
 *    is now a FALLBACK: it covers un-migrated content and the welded-footnote
 *    markers the backend deliberately leaves for their own repair.
 *  - `[1]` / `[a]` inline brackets are an EAR-ONLY concern and stay here. The
 *    backend can't touch them: across the corpus they are overwhelmingly the
 *    author's own enumeration ("three things: [1] Wisdom. [2] Authority.") —
 *    prose the page must keep. So they are kept for the eye and dropped only on
 *    the way to the engine.
 *
 * Also removed: anything `aria-hidden` — marked as not for assistive tech, so
 * not for TTS.
 *
 * The `<sup>` fallback is deliberately DOM-based (not a string regex over
 * innerHTML): removing `<sup>` nodes can't be confused with prose that merely
 * contains a digit. The bracket rule INFERS a footnote marker from its shape,
 * which is inherently approximate at the edges — a roman-numeral ref `[iv]`
 * reads as a word (kept, because `[is]`/`[in]` are real editor words), and a
 * single uppercase `[I]` is kept for the same reason (it is an inserted word or
 * a roman numeral, never a footnote letter — those are lowercase `[a]`, `[b]`).
 *
 * `FOOTNOTE_MARKER` and `isFootnoteMarker` are exported so the surfaces that
 * cannot use `spokenText` directly — the shareable quote card and the search
 * index — reuse this one definition rather than re-deriving it.
 */

// A bracketed footnote marker, plus one optional space in front so removing
// "much. [2]" leaves "much." and not "much. ". A short number, or a single
// LOWERCASE letter — the shape a footnote reference takes. Multi-letter brackets
// like "[him]" and an uppercase "[I]" are the editor's word (or a roman
// numeral), not a marker, and are kept.
export const FOOTNOTE_MARKER = /\s?\[(?:\d{1,3}|[a-z])\]/g;

/** The DOM half of the definition: is this element a footnote marker itself
 *  (a `<sup>`) or otherwise eye-only (`aria-hidden`)? Since the import-time
 *  strip landed, the `<sup>` case here is a fallback — see the header. */
export function isFootnoteMarker(el: Element): boolean {
	return el.tagName === 'SUP' || el.getAttribute('aria-hidden') === 'true';
}

// Block-level tags whose boundaries are a word break: a `<blockquote>` holding
// two `<p>`s must read "…end. Start…", never "…end.Start…". Only the blocks
// that actually occur in chapter prose — <br> is handled on its own below.
const BLOCK = /^(?:P|DIV|BLOCKQUOTE|LI|H[1-6])$/;

/**
 * Reader-facing prose of a node, footnote markers removed and whitespace
 * normalised — what the listen engine (`spokenText`) and the shareable quote
 * card both want. Accepts any `Node`, so a caller can hand it a cloned
 * selection range (a `DocumentFragment`) as readily as a paragraph element.
 *
 * OFFSET-DESTRUCTIVE by design: it collapses runs of whitespace and inserts
 * spaces at block boundaries, so a character position in the result no longer
 * lines up with the source's `textContent`. That is fine for text bound for the
 * ear or a PNG, and wrong for anything pinned to offsets — highlights, notes,
 * search hits. Those use `blankFootnoteMarkers`, which preserves length.
 */
export function readerProse(root: Node): string {
	return collect(root)
		.replace(FOOTNOTE_MARKER, '')
		.replace(/\s+/g, ' ')
		.trim();
}

/** The text to read aloud for one prose block. See `readerProse`. */
export function spokenText(el: Element): string {
	return readerProse(el);
}

function collect(el: Node): string {
	let out = '';
	for (const node of el.childNodes) {
		if (node.nodeType === Node.TEXT_NODE) {
			out += node.textContent ?? '';
			continue;
		}
		if (node.nodeType !== Node.ELEMENT_NODE) continue;
		const e = node as Element;
		const tag = e.tagName;
		if (isFootnoteMarker(e)) continue;
		if (tag === 'BR') {
			out += ' ';
			continue;
		}
		const inner = collect(e);
		out += BLOCK.test(tag) ? ` ${inner} ` : inner;
	}
	return out;
}

/**
 * `textContent` of a node with every footnote marker blanked to spaces —
 * length-preserving, so it is safe for the offset-pinned surfaces.
 *
 * Highlights, notes and search hits are stored and rendered as character
 * offsets into a block's raw `textContent` (see `rangeMarks.ts`), and the code
 * that paints them walks the live text nodes. So the search index can't just
 * DELETE markers — that would shift every offset after one and land the
 * highlight on the wrong words. Instead each marker's characters are replaced
 * by an equal number of spaces: the string stays the same length (position for
 * position identical to `textContent`), a marker can no longer match a query,
 * and no hit can begin inside one or run across one.
 */
export function blankFootnoteMarkers(root: Node): string {
	const walk = (node: Node, hidden: boolean): string => {
		let out = '';
		for (const child of node.childNodes) {
			if (child.nodeType === Node.TEXT_NODE) {
				const data = child.textContent ?? '';
				out += hidden ? ' '.repeat(data.length) : data;
				continue;
			}
			if (child.nodeType !== Node.ELEMENT_NODE) continue;
			out += walk(child, hidden || isFootnoteMarker(child as Element));
		}
		return out;
	};
	// Blank the inline `[n]` markers last, replacing each match with spaces of
	// the same length so the total length is unchanged.
	return walk(root, false).replace(FOOTNOTE_MARKER, (m) => ' '.repeat(m.length));
}
