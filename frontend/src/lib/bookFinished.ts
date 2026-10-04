import type { BookDetail, BookSummary, PlanSummary } from '$lib/library-public';

/**
 * Where a reader can go from a book they have just finished (BookFinished):
 * more by the same author, the plans that read this book, and books like it.
 *
 * Pure, so the page stays a view. Each list leaves out this book, its other
 * editions (shown in their own section) and anything the reader has already
 * finished, and no book is offered twice — an author's book is not repeated
 * under "More like this".
 */
export function finishedPicks({
	book,
	catalog,
	plans,
	progress,
	max
}: {
	book: BookDetail;
	/** This language's library (`libraryBooks`); empty until it lands. */
	catalog: BookSummary[];
	plans: PlanSummary[];
	progress: (slug: string) => { finished: boolean };
	max: number;
}): { moreByAuthor: BookSummary[]; plans: PlanSummary[]; related: BookSummary[] } {
	const seen = new Set([book.slug, ...(book.editions ?? []).map((e) => e.slug)]);
	const fresh = (b: BookSummary) => !seen.has(b.slug) && !progress(b.slug).finished;
	const take = (list: BookSummary[]) => {
		const out = list.filter(fresh).slice(0, max);
		for (const b of out) seen.add(b.slug);
		return out;
	};
	// Catalogue order (the library's own) is kept.
	const moreByAuthor = take(catalog.filter((b) => b.author.slug === book.author.slug));
	const related = take(book.related ?? []);
	const withThis = plans.filter((p) => p.covers.some((c) => c.slug === book.slug)).slice(0, 3);
	return { moreByAuthor, plans: withThis, related };
}
