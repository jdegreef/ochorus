/**
 * Whether the page at `path` (locale already stripped) already shows the
 * reader's current book, so the footer's "Continue reading" card would only
 * repeat it: home (the hero resumes it), the reader's own lists of what they
 * are reading (/reading, /favorites), and that book's detail and chapter pages.
 */
const LISTS_IT = ['/', '/reading', '/favorites'];

export function pageShowsBook(path: string, slug: string): boolean {
	const p = path.length > 1 ? path.replace(/\/+$/, '') : path;
	return LISTS_IT.includes(p) || `${p}/`.startsWith(`/books/${slug}/`);
}
