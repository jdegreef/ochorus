/**
 * A pure helper over an article's server-rendered `body_html` — the sanitized
 * HTML the API sends (see backend `ArticleDetailSerializer`). It reads the
 * string; it never builds HTML, so nothing here needs escaping.
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
