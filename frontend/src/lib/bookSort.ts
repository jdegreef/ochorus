/**
 * Filter-and-sort primitives for a shelf of books, shared by the /books shelf
 * (BooksShelf) and the topic page's Books section so the two stay in lockstep.
 * Pure and non-mutating — the caller holds the state; these just transform an
 * array. The query is expected pre-normalised (trimmed + lower-cased) by the
 * caller, which already lower-cases once per keystroke rather than once per book.
 */

export type BookSort = 'shelf' | 'title' | 'longest' | 'shortest';

interface SortableBook {
	title: string;
	subtitle?: string | null;
	author: { name: string };
	word_count?: number | null;
}

/**
 * Does a book match a filter query? `q` must already be trimmed and
 * lower-cased. An empty `q` means "no filter" and matches everything, so a
 * caller can pass the query straight through without a separate empty check.
 */
export function matchesBookQuery(book: SortableBook, q: string): boolean {
	if (!q) return true;
	return (
		book.title.toLowerCase().includes(q) ||
		(book.subtitle ?? '').toLowerCase().includes(q) ||
		book.author.name.toLowerCase().includes(q)
	);
}

/**
 * A new array of `books` in the given order. `shelf` preserves the input order
 * (the API's curated sort); `title` is locale-aware A–Z; `longest`/`shortest`
 * key off word_count (a missing count sorts as 0). Never mutates the input.
 */
export function sortBooks<T extends SortableBook>(books: readonly T[], sort: BookSort): T[] {
	const arr = [...books];
	switch (sort) {
		case 'title':
			return arr.sort((a, b) => a.title.localeCompare(b.title));
		case 'longest':
			return arr.sort((a, b) => (b.word_count ?? 0) - (a.word_count ?? 0));
		case 'shortest':
			return arr.sort((a, b) => (a.word_count ?? 0) - (b.word_count ?? 0));
		default:
			return arr;
	}
}
