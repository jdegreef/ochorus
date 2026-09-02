/**
 * The text to read aloud for one prose block.
 *
 * The reader speaks one paragraph per utterance, and the naive `el.innerText`
 * includes bits that are on the page for the eye, not the ear — footnote
 * reference markers most of all. A `<sup>4</sup>` after a sentence, or an
 * inline `[2]`, gets voiced as "…grace **four**" / "…much **two**", which
 * derails the listen. This strips those before they reach the engine.
 *
 * What it removes:
 *  - `<sup>` elements — in this corpus they are always footnote markers
 *    (numbered or empty), never exponents or ordinals.
 *  - `[1]` / `[a]` style inline footnote references — a bracketed number or a
 *    single letter. Multi-letter brackets like `[him]` are the editor's own
 *    words inserted into a quotation and ARE read, so they're kept.
 *  - anything `aria-hidden` — marked as not for assistive tech, so not for TTS.
 *
 * It is deliberately DOM-based (not a string regex over innerHTML): removing
 * `<sup>` nodes can't be confused with prose that merely contains a digit.
 *
 * These rules INFER what a footnote marker is from its shape, because the
 * backend importer doesn't tag them semantically. That's good enough for the
 * current corpus but brittle at the edges (a roman-numeral ref `[iv]`, an
 * editor's single-letter insertion `[I]`, a genuine `<sup>` exponent). The
 * durable fix is for the importer to emit an explicit class (`<sup class="fn">`
 * / `<a class="footnote-ref">`) and strip on that — see the book-import skill.
 */

// A bracketed footnote marker, plus one optional space in front so removing
// "much. [2]" leaves "much." and not "much. ". A single letter or short number;
// multi-letter brackets like "[him]" are the editor's word and are kept.
const FOOTNOTE_MARKER = /\s?\[(?:\d{1,3}|[a-zA-Z])\]/g;

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
