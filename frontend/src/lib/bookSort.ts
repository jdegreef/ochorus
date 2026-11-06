/**
 * Filter-and-sort primitives for a shelf of books, shared by the /books shelf
 * (BooksShelf) and the topic page's Books section so the two stay in lockstep.
 * Pure and non-mutating — the caller holds the state; these just transform an
 * array. The query is expected pre-normalised (trimmed + lower-cased) by the
 * caller, which already lower-cases once per keystroke rather than once per book.
 */

export const BOOK_SORTS = ['shelf', 'title', 'longest', 'shortest'] as const;
export type BookSort = (typeof BOOK_SORTS)[number];
/** Each sort's label key. */
export const BOOK_SORT_LABEL: Record<BookSort, string> = {
	shelf: 'common.sortShelf',
	title: 'common.sortTitle',
	longest: 'common.sortLongest',
	shortest: 'common.sortShortest'
};

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

/**
 * The shelf's length filter: a book is "short" (under an hour), "mid" (one to
 * three hours, inclusive) or "long" (over three), by the SAME whole-minute
 * reading time its card and list row print (`readingMinutes`, at the reader's
 * pace), so a book shown as "3 hr read" never filters as long. Pure: minutes
 * in, bucket out; the caller supplies the minutes. The sermons' buckets
 * (`$lib/sermonLength`) are minutes, not hours, so they are their own.
 */
export const BOOK_LENGTHS = ['short', 'mid', 'long'] as const;
export type BookLength = (typeof BOOK_LENGTHS)[number];
/** Each bucket's label key. */
export const BOOK_LENGTH_LABEL: Record<BookLength, string> = {
	short: 'books.lengthShort',
	mid: 'books.lengthMid',
	long: 'books.lengthLong'
};

export function bookLength(minutes: number): BookLength {
	if (minutes < 60) return 'short';
	if (minutes <= 180) return 'mid';
	return 'long';
}
