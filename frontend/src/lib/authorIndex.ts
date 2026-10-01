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

import { splitEdition } from './edition';
import { foldText } from './searchNormalize';

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
	const c = foldText(name.trim())[0]?.toUpperCase() ?? '';
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

/**
 * One line of a writer's list: a book, with any young-reader editions of it
 * (`<base>-teens`, `<base>-children` — see CLAUDE.md "young-reader edition")
 * folded beneath it as chips. Without this, one memoir with both retellings
 * reads as three books.
 */
export interface IndexRow<B extends IndexBook<IndexAuthor>> {
	book: B;
	/** Teens first, then Children — the backend's full → teens → children order. */
	editions: IndexEdition<B>[];
}

export interface IndexEdition<B extends IndexBook<IndexAuthor>> {
	book: B;
	/** "For Teens", read from the edition's own (already translated) title. */
	audience: string;
}

export interface IndexRowEntry<A extends IndexAuthor, B extends IndexBook<IndexAuthor>> {
	author: A;
	rows: IndexRow<B>[];
}

export interface IndexRowGroup<A extends IndexAuthor, B extends IndexBook<IndexAuthor>> {
	letter: string;
	entries: IndexRowEntry<A, B>[];
}

const EDITION_SUFFIX = /-(teens|children)$/;

/**
 * Fold each young-reader edition under its full text, by slug alone — the same
 * link `serializers.sibling_editions` derives. An edition whose `<base>` is not
 * in this list (e.g. a translated retelling whose full text has no row in this
 * language, or `the-body-of-christ-teens` whose parent has another slug) stays
 * a line of its own, so nothing is dropped — as does one whose title carries
 * no "(For …)" to label its chip with. Order of the input is kept.
 */
export function foldEditions<B extends IndexBook<IndexAuthor>>(books: B[]): IndexRow<B>[] {
	const bySlug = new Map(books.map((b) => [b.slug, b]));
	const editionsOf = new Map<string, IndexEdition<B>[]>();
	const folded = new Set<string>();
	for (const b of books) {
		const m = b.slug.match(EDITION_SUFFIX);
		const split = m && splitEdition(b.slug, b.title);
		if (!m || !split) continue;
		const base = b.slug.slice(0, -m[0].length);
		if (!bySlug.has(base) || EDITION_SUFFIX.test(base)) continue;
		const list = editionsOf.get(base) ?? [];
		list.push({ book: b, audience: split.audience });
		editionsOf.set(base, list);
		folded.add(b.slug);
	}
	const rank = (e: IndexEdition<B>) => (e.book.slug.endsWith('-teens') ? 0 : 1);
	return books
		.filter((b) => !folded.has(b.slug))
		.map((book) => ({
			book,
			editions: (editionsOf.get(book.slug) ?? []).sort((x, y) => rank(x) - rank(y))
		}));
}

/** `authorIndex` groups, with each writer's books folded into rows. */
export function indexRows<A extends IndexAuthor, B extends IndexBook<IndexAuthor>>(
	groups: IndexGroup<A, B>[]
): IndexRowGroup<A, B>[] {
	return groups.map((g) => ({
		letter: g.letter,
		entries: g.entries.map((e) => ({
			author: e.author,
			rows: foldEditions(e.books)
		}))
	}));
}

/**
 * Narrow the index to a typed query. A writer whose NAME matches keeps every
 * book; otherwise a writer stays only for the rows whose title (or an
 * edition's title) matches, so "humility" finds Murray with just that book.
 * Empty writers and letters drop out. A blank query returns the input as is.
 */
export function filterIndex<A extends IndexAuthor, B extends IndexBook<IndexAuthor>>(
	groups: IndexRowGroup<A, B>[],
	query: string
): IndexRowGroup<A, B>[] {
	const q = foldText(query.trim());
	if (!q) return groups;
	const hit = (s: string) => foldText(s).includes(q);
	return groups
		.map((g) => ({
			letter: g.letter,
			entries: g.entries.flatMap((e) => {
				if (hit(e.author.name)) return [e];
				const rows = e.rows.filter((r) => hit(r.book.title) || r.editions.some((x) => hit(x.book.title)));
				return rows.length ? [{ author: e.author, rows }] : [];
			})
		}))
		.filter((g) => g.entries.length > 0);
}
