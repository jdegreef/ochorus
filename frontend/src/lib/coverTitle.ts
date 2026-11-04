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

/**
 * A young-reader edition's title split into the WORDS a cover sets large and
 * the EDITION it sets as a tracked line under them: « Absolute Surrender (For
 * Teens) » → `Absolute Surrender` + `For Teens`, es « El progreso del peregrino
 * (para jóvenes) » → … + `para jóvenes`. The designed English covers have
 * always set the edition that way ("— FOR TEENS —"); the painted and drawn
 * ones carried it as a bracket inside the display type, a whole line of it,
 * in four capitalisations across the translations (2026-11-01).
 *
 * Only a young edition (slug `<base>-teens` / `<base>-children`, the
 * sibling-editions convention) whose set title ENDS in a bracket — so *Come Ye
 * Children* keeps its words, and a title with no bracket is set as it was.
 */
export function editionOf(slug: string, title: string): { words: string; edition: string | null } {
	if (!/-(teens|children)$/.test(slug)) return { words: title, edition: null };
	const m = /^(.*\S)\s*[(（]([^()（）]+)[)）]\s*$/u.exec(title);
	return m ? { words: m[1], edition: m[2].trim() } : { words: title, edition: null };
}
