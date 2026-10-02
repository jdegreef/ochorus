import type { BookTile, PlanDetail, PlanSummary } from './library-public';
import { ORIGINALS_SLUG } from './originals';

/** At most this many plans in the plan page's "More like this" — one row of the shelf's three-up grid. */
export const RELATED_PLANS_LIMIT = 3;
/** A shared source book is the strong signal (it IS the same theme); a shared writer the weaker one. */
const BOOK_WEIGHT = 2;
const AUTHOR_WEIGHT = 1;

/** The writers of a cover strip's books (a list-row plan's strip holds up to five). The house
 *  imprint is not a writer: it bylines unrelated series (Rooted, Brave for God, …), so sharing it
 *  says nothing about theme — the same reason the A–Z leaves it out. */
const authorsOf = (covers: BookTile[]) =>
	covers.flatMap((c) => (c.author?.slug && c.author.slug !== ORIGINALS_SLUG ? [c.author.slug] : []));
/** How many of `theirs` are also in `mine`. */
const shared = (theirs: Iterable<string>, mine: Set<string>) => new Set([...theirs].filter((s) => mine.has(s))).size;

/**
 * The plans most like `plan`, best first: each candidate scores BOOK_WEIGHT per
 * source book it shares and AUTHOR_WEIGHT per writer it shares. Plans carry no
 * topic of their own, so a shared book stands in for a shared theme. Candidates
 * come from `all` — the plans list in the CURRENT language, so every suggestion
 * opens here (no English fallback) — minus the plan itself and anything scoring
 * 0. Ties keep the shelf's own (curated) order, so the result is deterministic.
 *
 * A candidate is read from its list row, whose cover strip names at most FIVE
 * of its books (`_plan_covers`), so a book or writer met only in a long plan's
 * sixth source onwards is not counted for it. Accepted: few plans run past five
 * books, and those are house-written series whose writer the first five carry.
 * An empty result means "omit the block", never an empty heading.
 */
export function relatedPlans(
	plan: Pick<PlanDetail, 'slug' | 'days' | 'authors' | 'covers'>,
	all: PlanSummary[],
	limit = RELATED_PLANS_LIMIT
): PlanSummary[] {
	// The detail payload names every book (its days) and every writer; the
	// cover strip backs up `authors` from an API predating that field.
	const books = new Set(plan.days.flatMap((d) => (d.book_slug ? [d.book_slug] : [])));
	const authors = new Set(
		[...(plan.authors ?? []).map((a) => a.slug), ...authorsOf(plan.covers)].filter((s) => s !== ORIGINALS_SLUG)
	);
	return all
		.map((p, index) => {
			const theirBooks = p.covers.map((c) => c.slug);
			const score = shared(theirBooks, books) * BOOK_WEIGHT + shared(authorsOf(p.covers), authors) * AUTHOR_WEIGHT;
			return { p, index, score };
		})
		.filter((x) => x.p.slug !== plan.slug && x.score > 0)
		.sort((a, b) => b.score - a.score || a.index - b.index)
		.slice(0, limit)
		.map((x) => x.p);
}
