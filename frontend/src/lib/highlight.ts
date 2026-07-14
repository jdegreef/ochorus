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

/**
 * A client snippet: a window of `text` around the first case-insensitive match
 * of `query`, with the match wrapped in `<mark>`. Used by the in-book search,
 * which searches cached chapter text on the device. Falls back to the head of
 * the text when the query isn't found in this block.
 */
export function highlightAround(text: string, query: string, radius = 60): string {
	const idx = text.toLowerCase().indexOf(query.toLowerCase());
	if (idx < 0) return escapeHtml(text.slice(0, 140));
	const start = Math.max(0, idx - radius);
	const end = Math.min(text.length, idx + query.length + radius);
	const before = (start > 0 ? '… ' : '') + escapeHtml(text.slice(start, idx));
	const match = escapeHtml(text.slice(idx, idx + query.length));
	const after = escapeHtml(text.slice(idx + query.length, end)) + (end < text.length ? ' …' : '');
	return `${before}<mark>${match}</mark>${after}`;
}
