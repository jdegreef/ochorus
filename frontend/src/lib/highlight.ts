/**
 * Snippet highlighting for search results, shared by the in-book search drawer
 * (which windows a match client-side) and the library search page (which shows
 * server snippets with the match wrapped in full-text markers). Text is always
 * escaped first, so the only HTML produced is the `<mark>` tags inserted here.
 */

/** The markers the backend (SearchHeadline / fallback_snippet) wraps matches in. */
const HL_START = '⟦';
const HL_END = '⟧';

/** Escape the HTML-significant characters so a snippet can't inject markup. */
export function escapeHtml(s: string): string {
	return s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]!);
}

/**
 * A server snippet: escape it, then turn the full-text markers into `<mark>`
 * spans. Used by the library-wide search page.
 */
export function markSnippet(snippet: string): string {
	return escapeHtml(snippet).replaceAll(HL_START, '<mark>').replaceAll(HL_END, '</mark>');
}

/** One run of a snippet: plain text, or a matched word to draw as `<mark>`. */
export interface SnippetPart {
	text: string;
	mark: boolean;
}

/**
 * The fallback matcher for `query`: the whole query, as whole words, any case.
 * Compiled once per query rather than once per row — the page renders thirty
 * rows off the same one.
 */
let fallbackFor = '';
let fallbackRe: RegExp | null = null;
function fallbackMatcher(query: string): RegExp | null {
	const q = query.trim().replace(/\s+/g, ' ');
	if (q !== fallbackFor) {
		fallbackFor = q;
		fallbackRe = null;
		if (q.length >= 2) {
			// Whole words only (no "all" inside "called"), and the phrase as a
			// whole: marking "of" alone for "all of grace" would claim a match
			// the server never made.
			try {
				fallbackRe = new RegExp(
					`(?<![\\p{L}\\p{N}])(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/ /g, '\\s+')})(?![\\p{L}\\p{N}])`,
					'giu'
				);
			} catch {
				// Lookbehind is a SyntaxError before Safari/WKWebView 16.4, and the
				// iOS app still targets iOS 15: there the snippet is simply shown
				// unmarked rather than taking the results list down with it.
				fallbackRe = null;
			}
		}
	}
	return fallbackRe;
}

/**
 * A server snippet as runs of text, for a template to render with `{#each}` —
 * no HTML string, so nothing in it can ever be read as markup.
 *
 * The server's full-text markers decide what is marked. A snippet that carries
 * none (an entity's description, a fallback excerpt) falls back to marking the
 * query itself where it appears as whole words, so a row never claims a match
 * it doesn't have and rarely hides one it does.
 */
export function snippetParts(snippet: string, query = ''): SnippetPart[] {
	if (snippet.includes(HL_START)) {
		const parts: SnippetPart[] = [];
		for (const [i, run] of snippet.split(HL_START).entries()) {
			const end = i === 0 ? -1 : run.indexOf(HL_END);
			if (end < 0) {
				parts.push({ text: run, mark: false });
				continue;
			}
			parts.push({ text: run.slice(0, end), mark: true });
			parts.push({ text: run.slice(end + HL_END.length), mark: false });
		}
		return parts.filter((p) => p.text);
	}
	const re = fallbackMatcher(query);
	if (!re) return snippet ? [{ text: snippet, mark: false }] : [];
	// split() with one capturing group alternates text, match, text, match…
	return snippet
		.split(re)
		.map((text, i) => ({ text, mark: i % 2 === 1 }))
		.filter((p) => p.text);
}

/** Whether the server marked a match in `snippet` (its full-text markers). */
export const hasServerMarks = (snippet: string) => snippet.includes(HL_START);

/**
 * A window of `text` around the span [idx, idx+len), with that span wrapped in
 * `<mark>`. The caller has already located the match (a literal `indexOf`, or a
 * normalized/stemmed word span — see searchNormalize); this only renders the
 * window. Everything is HTML-escaped, so the sole markup is the `<mark>`.
 */
export function windowAt(text: string, idx: number, len: number, radius = 60): string {
	const start = Math.max(0, idx - radius);
	const end = Math.min(text.length, idx + len + radius);
	const before = (start > 0 ? '… ' : '') + escapeHtml(text.slice(start, idx));
	const match = escapeHtml(text.slice(idx, idx + len));
	const after = escapeHtml(text.slice(idx + len, end)) + (end < text.length ? ' …' : '');
	return `${before}<mark>${match}</mark>${after}`;
}

/**
 * A client snippet: a window of `text` around the first case-insensitive match
 * of `query`, with the match wrapped in `<mark>`. Used by the in-book search,
 * which searches cached chapter text on the device. Falls back to the head of
 * the text when the query isn't found in this block.
 */
export function highlightAround(text: string, query: string, radius = 60): string {
	const idx = text.toLowerCase().indexOf(query.toLowerCase());
	if (idx < 0) return escapeHtml(text.slice(0, 140));
	return windowAt(text, idx, query.length, radius);
}
