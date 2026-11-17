/**
 * Paragraph anchors: a citable address for every paragraph of a chapter,
 * sermon or biography.
 *
 * The reader's paragraph unit is the body's top-level element (`?p=N` is an
 * index into `body.children`: bookmarks, highlights, search hits). Giving each
 * of those elements `id="p-N"` in the prerendered HTML lets a link — or an
 * answer engine quoting us — point at one paragraph with a plain `#p-N`
 * fragment that works with no script at all, and the reader treats that
 * fragment exactly like `?p=N`.
 */

const VOID = new Set([
	'area',
	'base',
	'br',
	'col',
	'embed',
	'hr',
	'img',
	'input',
	'link',
	'meta',
	'source',
	'track',
	'wbr'
]);
/** Elements whose content is raw text, never tags. */
const RAW = new Set(['script', 'style', 'textarea', 'title']);

const TAG = /<!--[\s\S]*?-->|<(\/?)([a-zA-Z][\w-]*)((?:[^>"']|"[^"]*"|'[^']*')*)>/g;

/** The fragment id of paragraph `n`. */
export const paragraphId = (n: number) => `p-${n}`;

/**
 * Add `id="p-N"` to each top-level element of `html`, N being its index among
 * the top-level ELEMENTS (text between them is not counted, as
 * `Element.children` does not count it). An element that already has an id
 * keeps it.
 */
export function anchorParagraphs(html: string): string {
	let depth = 0;
	let index = 0;
	let out = '';
	let last = 0;
	let raw: string | null = null;
	TAG.lastIndex = 0;
	for (let m; (m = TAG.exec(html)); ) {
		const [whole, close, rawName, attrs] = m;
		if (whole.startsWith('<!--') || rawName === undefined) continue;
		const name = rawName.toLowerCase();
		if (raw) {
			if (close && name === raw) {
				raw = null;
				depth--;
			}
			continue;
		}
		if (close) {
			depth = Math.max(0, depth - 1);
			continue;
		}
		const selfClosing = VOID.has(name) || /\/\s*$/.test(attrs);
		if (depth === 0) {
			const n = index++;
			if (!/(^|\s)id\s*=/i.test(attrs)) {
				const at = m.index + 1 + rawName.length;
				out += html.slice(last, at) + ` id="${paragraphId(n)}"`;
				last = at;
			}
		}
		if (!selfClosing) {
			depth++;
			if (RAW.has(name)) raw = name;
		}
	}
	return out + html.slice(last);
}

/** `#p-12` → 12; anything else → null. */
export function paragraphFromHash(hash: string): number | null {
	const m = /^#p-(\d+)$/.exec(hash);
	return m ? Number(m[1]) : null;
}

/**
 * The address of paragraph `p` on the page at `url`: the page's own URL with
 * its `?p=` and fragment replaced, so a copied quote links to the paragraph it
 * came from rather than to the top of the chapter.
 */
export function paragraphUrl(url: string, p: number | undefined): string {
	if (p === undefined || !Number.isInteger(p) || p < 0) return url;
	try {
		const u = new URL(url);
		u.searchParams.delete('p');
		u.hash = paragraphId(p);
		return u.toString();
	} catch {
		return url;
	}
}
