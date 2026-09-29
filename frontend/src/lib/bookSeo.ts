/**
 * The free download formats an edition offers, named the way people search for
 * them ("<title> pdf", "<title> epub"): "PDF & EPUB", "EPUB", "PDF" or "".
 */
export const downloadFormats = (book: { pdf_url?: string; epub_url?: string }): string =>
	[book.pdf_url && 'PDF', book.epub_url && 'EPUB'].filter(Boolean).join(' & ');

/**
 * A book's <title> with its download formats, when it has any.
 *
 * "<title> pdf" is one of the commonest ways a classic is searched for, and a
 * title that says the file is here is what earns that click. The format names
 * are the same in every language, so they are appended to each locale's own
 * reviewed title rather than translated. The " — Ochorus" suffix gives way to
 * make room: it is the least load-bearing part, and Google prints the site
 * name above the result anyway.
 */
export function titleWithFormats(title: string, formats: string): string {
	if (!formats) return title;
	return `${title.replace(/\s+—\s+Ochorus$/, '')} (${formats})`;
}
