/**
 * Pure helpers over an article's server-rendered `body_html` — the sanitized
 * HTML the API sends (see backend `ArticleDetailSerializer`). They read the
 * string; they never build HTML, so nothing here needs escaping.
 */

/**
 * Split the body just before its `n`th `<h2` (1-based), so the page can set
 * something between two sections — the mid-article "read it in full" card.
 * `null` when the body has fewer than `n` sections: the caller then renders
 * it whole. Cutting at a tag's `<` keeps both halves well-formed, because the
 * body is a flat run of top-level blocks (p / h2 / ul / blockquote).
 */
export function splitBeforeSection(html: string, n: number): [string, string] | null {
	let at = -1;
	for (let i = 0; i < n; i++) {
		at = html.indexOf('<h2', at + 1);
		if (at === -1) return null;
	}
	return at > 0 ? [html.slice(0, at), html.slice(at)] : null;
}

const REF = /<a\b[^>]*\bclass="scripture-ref"[^>]*\bdata-ref="([^"]+)"/g;

/** The Bible references the body cites, in order of first mention, once each —
 *  the server-wrapped `<a class="scripture-ref" data-ref="…">` spans. */
export function scriptureRefs(html: string): string[] {
	const seen = new Set<string>();
	for (const [, raw] of html.matchAll(REF)) {
		seen.add(raw.replace(/&amp;/g, '&').replace(/&#39;/g, "'").replace(/&quot;/g, '"'));
	}
	return [...seen];
}
