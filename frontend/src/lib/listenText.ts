/**
 * The text to read aloud for one prose block.
 *
 * The reader speaks one paragraph per utterance, and the naive `el.innerText`
 * includes bits that are on the page for the eye, not the ear — footnote
 * reference markers most of all. A `<sup>4</sup>` after a sentence, or an
 * inline `[2]`, gets voiced as "…grace **four**" / "…much **two**", which
 * derails the listen. This strips those before they reach the engine.
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
 */

// A bracketed footnote marker, plus one optional space in front so removing
// "much. [2]" leaves "much." and not "much. ". A short number, or a single
// LOWERCASE letter — the shape a footnote reference takes. Multi-letter brackets
// like "[him]" and an uppercase "[I]" are the editor's word (or a roman
// numeral), not a marker, and are kept.
const FOOTNOTE_MARKER = /\s?\[(?:\d{1,3}|[a-z])\]/g;

// Block-level tags whose boundaries are a word break: a `<blockquote>` holding
// two `<p>`s must read "…end. Start…", never "…end.Start…". Only the blocks
// that actually occur in chapter prose — <br> is handled on its own below.
const BLOCK = /^(?:P|DIV|BLOCKQUOTE|LI|H[1-6])$/;

export function spokenText(el: Element): string {
	return collect(el)
		.replace(FOOTNOTE_MARKER, '')
		.replace(/\s+/g, ' ')
		.trim();
}

function collect(el: Element): string {
	let out = '';
	for (const node of el.childNodes) {
		if (node.nodeType === Node.TEXT_NODE) {
			out += node.textContent ?? '';
			continue;
		}
		if (node.nodeType !== Node.ELEMENT_NODE) continue;
		const e = node as Element;
		const tag = e.tagName;
		if (tag === 'SUP' || e.getAttribute('aria-hidden') === 'true') continue;
		if (tag === 'BR') {
			out += ' ';
			continue;
		}
		const inner = collect(e);
		out += BLOCK.test(tag) ? ` ${inner} ` : inner;
	}
	return out;
}
