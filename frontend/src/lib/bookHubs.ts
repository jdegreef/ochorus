import type { BookSummary, Hub } from '$lib/library-public';
import { ERAS, eraOf, type EraId } from '$lib/eras';

/**
 * Book hubs: the library's books by tradition (/books/tradition/<slug>/) and by
 * era (/books/era/<era>/), the biography hubs' twins for "Puritan books" and
 * "early church fathers writings" searches.
 *
 * A book belongs where its AUTHOR does: a tradition hub's members
 * (`library/data/hubs/members.json`, the same list /biographies/tradition/
 * reads) or the era of the author's birth year (`$lib/eras`, as
 * /biographies/era/ files them). A house imprint is no one's tradition or era,
 * and a young-reader edition (`-children`, `-teens`) stays on its own hub, so
 * neither is listed here.
 *
 * Pure, so the routes stay markup and this stays tested.
 */

/** Fewer books than this, or books by one writer alone (that is an author
 *  page), and a hub gets no page: it 404s, and every link to it checks
 *  `hasPage` first, so the crawler never meets a missing one. */
export const BOOK_HUB_FLOOR = 4;

export const hasPage = (books: BookSummary[]) =>
	books.length >= BOOK_HUB_FLOOR && writerCount(books) >= 2;

export const bookTraditionPath = (slug: string) => `/books/tradition/${slug}/`;
export const bookEraPath = (era: EraId) => `/books/era/${era}/`;

const YOUNG = /-(children|teens)$/;

/** The books a hub can list: a real person's, full editions only. */
const listable = (books: BookSummary[]) =>
	books.filter((b) => !b.author.is_imprint && !YOUNG.test(b.slug));

/** Earliest-born writer first (undated last), keeping the shelf's own order
 *  within a writer — the biography hubs' order. */
const byWriter = (books: BookSummary[]) =>
	books
		.map((b, i) => ({ b, i }))
		.sort(
			(x, y) =>
				(x.b.author.birth_year ?? 9999) - (y.b.author.birth_year ?? 9999) ||
				x.b.author.name.localeCompare(y.b.author.name) ||
				x.i - y.i
		)
		.map(({ b }) => b);

/** A tradition hub's books. */
export function traditionBooks(hub: Pick<Hub, 'members'>, books: BookSummary[]): BookSummary[] {
	const members = new Set(hub.members);
	return byWriter(listable(books).filter((b) => members.has(b.author.slug)));
}

/** An era's books. Undated writers are left out, unlike the biography eras
 *  (which file them as modern): an undated writer is as often an early Father
 *  (Hermas, Minucius Felix) as a living one, and a misfiled book is worse than
 *  a missing one. */
export const eraBooks = (era: EraId, books: BookSummary[]): BookSummary[] =>
	byWriter(
		listable(books).filter((b) => b.author.birth_year != null && eraOf(b.author.birth_year) === era)
	);

/** The tradition hubs with a book page in this language, in the hubs' order. */
export const traditionsWithBooks = (hubs: Hub[], books: BookSummary[]): Hub[] =>
	hubs.filter((h) => h.kind === 'tradition' && hasPage(traditionBooks(h, books)));

/** The eras with a book page in this language, earliest first. */
export const erasWithBooks = (books: BookSummary[]): EraId[] =>
	ERAS.map((e) => e.id).filter((id) => hasPage(eraBooks(id, books)));

/** How many writers a list of books is by. */
export const writerCount = (books: BookSummary[]) => new Set(books.map((b) => b.author.slug)).size;
