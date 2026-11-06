/**
 * The biography's opening, for the author page (design review #14): the page
 * shows about the first three paragraphs and folds the rest behind "Continue
 * reading the biography", so the books and sermons are not 1,500 words down.
 *
 * The fold is an attribute, not a cut. `foldBio` marks the first top-level
 * element past the opening with `data-bio-fold`, and the page's CSS hides it
 * and everything after it while the fold is closed. The whole life stays in
 * the prerendered HTML (search engines read it), and <Reader> still holds ONE
 * body, so paragraph indices — resume points, highlights, `?p=` links, read
 * aloud — mean what they meant before.
 *
 * A string pass rather than the DOM, because it has to run during prerender.
 * The bio is server-cleaned flat HTML: top-level <p>, <h2>, <blockquote>,
 * prayer-callout <div>s. Only top-level elements count; a <p> inside a
 * blockquote or a callout is part of that block.
 */

export const FOLD_ATTR = 'data-bio-fold';

const VOID = new Set(['br', 'hr', 'img', 'wbr', 'input', 'source', 'col', 'area', 'meta', 'link']);

/** Each top-level element's tag and where its opening `<` sits. */
function topLevel(html: string): { tag: string; at: number }[] {
	const out: { tag: string; at: number }[] = [];
	// Attribute values are skipped whole, so a `/` or `>` inside one is not
	// read as the end of the tag.
	const re = /<(\/?)([a-zA-Z][\w-]*)\b(?:[^>"']|"[^"]*"|'[^']*')*?(\/?)>/g;
	let depth = 0;
	for (let m; (m = re.exec(html)); ) {
		const [, close, rawTag, selfClose] = m;
		const tag = rawTag.toLowerCase();
		if (close) {
			depth = Math.max(0, depth - 1);
			continue;
		}
		if (depth === 0) out.push({ tag, at: m.index });
		if (!selfClose && !VOID.has(tag)) depth++;
	}
	return out;
}

/**
 * `html` with the fold marked after its first `paragraphs` top-level <p>s —
 * so the opening always ends on a paragraph, never on a heading. Unchanged (and `folded: false`) when the rest would be under
 * `minRest` elements: a fold that hides one paragraph only costs a click.
 */
export function foldBio(html: string, paragraphs = 3, minRest = 2): { html: string; folded: boolean } {
	const els = topLevel(html);
	let seen = 0;
	const k = els.findIndex((e) => e.tag === 'p' && ++seen === paragraphs) + 1;
	if (k === 0) return { html, folded: false };
	if (els.length - k < minRest) return { html, folded: false };
	const { tag, at } = els[k];
	const cut = at + 1 + tag.length;
	return {
		html: `${html.slice(0, cut)} ${FOLD_ATTR}${html.slice(cut)}`,
		folded: true
	};
}
