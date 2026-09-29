/**
 * The library A–Z (/authors/): every writer, alphabetically, each with the
 * books of theirs published in this language.
 *
 * It is the one page that links EVERY author and EVERY book in its language
 * from a single, visible, indexable document. The browse shelves can't: Books
 * and Biographies page 24 at a time, so their prerendered HTML names only the
 * first page, and the rest of the library was reached by crawlers only through
 * other books. With this page in the footer, any work is two clicks from
 * anywhere. It is also the prerender's crawl anchor for the localized author
 * and era pages — see svelte.config.js — so it must stay complete and
 * unpaginated.
 */

export interface IndexAuthor {
	slug: string;
	name: string;
	birth_year: number | null;
	death_year: number | null;
}

export interface IndexBook<A extends IndexAuthor = IndexAuthor> {
	slug: string;
	title: string;
	author: A;
}

export interface IndexEntry<A extends IndexAuthor, B extends IndexBook<IndexAuthor>> {
	author: A;
	books: B[];
}

export interface IndexGroup<A extends IndexAuthor, B extends IndexBook<IndexAuthor>> {
	/** A–Z, or '#' for a name that doesn't start with a Latin letter. */
	letter: string;
	entries: IndexEntry<A, B>[];
}

/** The letter a name files under: its first letter, accents folded ("Á" → "A"). */
export function initialOf(name: string): string {
	const c = name.trim().normalize('NFD').replace(/[̀-ͯ]/g, '')[0]?.toUpperCase() ?? '';
	return c >= 'A' && c <= 'Z' ? c : '#';
}

/**
 * Writers grouped by initial, names in `locale` collation, each with their
 * books sorted by title. `skip` drops a slug that is not a person (the house
 * imprint, whose books have their own shelf).
 *
 * A book's author who is missing from `authors` is added from the book: the
 * writers list leaves out anyone hidden from Biographies or with nothing in
 * English, and their books would otherwise vanish from a page that promises
 * every book.
 */
export function authorIndex<A extends IndexAuthor, B extends IndexBook<IndexAuthor>>(
	authors: A[],
	books: B[],
	locale = 'en',
	skip: string[] = []
): IndexGroup<A | B['author'], B>[] {
	const collator = new Intl.Collator(locale, { sensitivity: 'base' });
	const byAuthor = new Map<string, B[]>();
	for (const b of books) {
		const list = byAuthor.get(b.author.slug) ?? [];
		list.push(b);
		byAuthor.set(b.author.slug, list);
	}
	const writers = new Map<string, A | B['author']>(authors.map((a) => [a.slug, a]));
	for (const b of books) if (!writers.has(b.author.slug)) writers.set(b.author.slug, b.author);
	const groups = new Map<string, IndexEntry<A | B['author'], B>[]>();
	for (const a of [...writers.values()].sort((x, y) => collator.compare(x.name, y.name))) {
		if (skip.includes(a.slug)) continue;
		const letter = initialOf(a.name);
		const own = (byAuthor.get(a.slug) ?? []).sort((x, y) => collator.compare(x.title, y.title));
		const list = groups.get(letter) ?? [];
		list.push({ author: a, books: own });
		groups.set(letter, list);
	}
	// '#' last, the letters in order.
	return [...groups.entries()]
		.sort(([x], [y]) => (x === '#' ? 1 : y === '#' ? -1 : x.localeCompare(y)))
		.map(([letter, entries]) => ({ letter, entries }));
}
