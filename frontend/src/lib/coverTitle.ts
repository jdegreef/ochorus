/**
 * The title a cover SETS: the book's short `cover_title` when it has one, else
 * its title. One function so `BookCover` and the share-twin script
 * (`generate-cover-og.mjs`) cannot disagree.
 *
 * Its own module rather than a line in `coverCardMarkup.ts` because the twin
 * script digests that file: any edit there redraws every card in the library.
 *
 * `tests_fixture._cover_title` is its Python twin (the twin digest is
 * recomputed there): change one, change both. Neither trims — the fixture
 * gate rejects an untrimmed value instead, so the two cannot disagree on
 * what whitespace is.
 *
 * Only the drawn words. A cover's accessible name, the book page, search and
 * every other surface keep the full title.
 */
export function coverTitle(book: { title: string; cover_title?: string | null }): string {
	return book.cover_title || book.title;
}
