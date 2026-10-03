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

/**
 * The title a search result should carry for this edition.
 *
 * A multi-volume work can name every volume alike — Simpson's "The Holy
 * Spirit, or Power from on High" is Part I and Part II, both under a series of
 * the same name — and then only the subtitle tells the volumes apart. Without
 * it, two pages share one <title>, and Google picks one and folds the other.
 * So when the series is named exactly as the book, the subtitle joins the
 * title; every other book keeps its plain title.
 */
export function distinctTitle(book: {
	title: string;
	subtitle?: string;
	series?: { title: string } | null;
}): string {
	return book.subtitle && book.series?.title === book.title
		? `${book.title}: ${book.subtitle}`
		: book.title;
}

/**
 * A chapter's meta description: its book and chapter, then its opening words.
 *
 * The opening alone collided — the Key Teachings volumes open chapters on the
 * same Scripture, a teens edition on its parent's epigraph, two Arabic Gareth
 * Evans books on one shared preface: 136 chapters in 56 identical pairs. The
 * book and chapter name are unique by construction and lead, so the
 * description is distinct before any truncation reaches the excerpt.
 */
export const chapterMeta = (bookTitle: string, chapter: string, opening: string): string =>
	`${bookTitle} — ${chapter}: ${opening.trim()}`;
