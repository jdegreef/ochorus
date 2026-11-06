/**
 * The named rows /books opens on (design review #11, "Books: curated rows
 * first"): a few short ways into the library instead of one flat grid of every
 * book. The full grid, with its filters, stays one tab away ("All N books").
 *
 * Built from the shelf the page already loads — no API call of its own — and
 * from curated signals that already exist rather than a second list to keep up:
 *
 * - **Start here**: the one hand list, `START_HERE`, in its own order — the
 *   works a newcomer to the classics is pointed at first. Kept short and here,
 *   nowhere else. A language that has too few of them (a young catalogue) tops
 *   the row up from the shelf's featured order (the API's `sort_order`),
 *   leaving out the young-reader editions, which have a row of their own.
 * - **Topic rows**: the editors' own topic membership, titled with the topic's
 *   own (translated) name. `ROW_TOPICS` names the topics to try, in order; one
 *   with too few books in this language is skipped, and the shelf's largest
 *   remaining topics fill in, so every language opens on the same number of
 *   rows when it has the books.
 *
 * Pure, so the selection is tested beside it (`browseRows.test.ts`).
 */

import { collapseEditions, editionKind } from './edition';

interface RowBook {
	slug: string;
	topics?: { slug: string; title: string }[];
}

/** The newcomer's first books, by slug — the only hand list. */
export const START_HERE = [
	'confessions',
	'pilgrims-progress',
	'the-pursuit-of-god',
	'the-imitation-of-christ',
	'the-inner-chamber',
	'the-practice-of-the-presence-of-god',
	'absolute-surrender',
	'all-of-grace',
	'humility-2',
	'the-way-to-god'
] as const;

/** The topics tried for the rows after Start here, in order: prayer, the
 *  devotional classics, the deeper life, and the young readers' shelf. */
export const ROW_TOPICS = ['prayer', 'enduring-classics', 'deeper-life', 'for-young-readers'] as const;

/** A row needs this many books to be worth a heading. */
export const ROW_MIN = 4;
/** The most books one row shows; "See all" has the rest. */
export const ROW_MAX = 12;


/** One row. `topic` is null for Start here; `count` is how many books the
 *  row's "See all" holds (a topic row shows at most `ROW_MAX`). */
export interface BrowseRow<T extends RowBook> {
	topic: { slug: string; title: string } | null;
	count: number;
	books: T[];
}

export function browseRows<T extends RowBook>(books: readonly T[]): BrowseRow<T>[] {
	const rows: BrowseRow<T>[] = [];

	const bySlug = new Map(books.map((b) => [b.slug, b]));
	const start = START_HERE.map((s) => bySlug.get(s)).filter((b): b is T => !!b);
	if (start.length < ROW_MIN) {
		const picked = new Set(start.map((b) => b.slug));
		for (const b of books) {
			if (start.length >= ROW_MIN * 2) break;
			if (!picked.has(b.slug) && !editionKind(b.slug)) start.push(b);
		}
	}
	if (start.length >= ROW_MIN) rows.push({ topic: null, count: start.length, books: start });

	// Every topic on the shelf, its books in shelf (featured) order.
	const topics = new Map<string, { topic: { slug: string; title: string }; books: T[] }>();
	for (const b of books) {
		for (const tc of b.topics ?? []) {
			const entry = topics.get(tc.slug) ?? { topic: tc, books: [] };
			entry.books.push(b);
			topics.set(tc.slug, entry);
		}
	}
	// One slot per work (design review #26): a topic's young-reader editions
	// fold into their full text when it is in the row too — the same rule, and
	// so the same count, as the "See all" grid the row links to.
	for (const e of topics.values()) e.books = collapseEditions(e.books);
	const big = (slug: string) => (topics.get(slug)?.books.length ?? 0) >= ROW_MIN;
	const chosen: string[] = ROW_TOPICS.filter(big);
	// Fallback: the largest remaining topics, until the row count matches.
	const rest = [...topics.values()]
		.filter((e) => !chosen.includes(e.topic.slug) && e.books.length >= ROW_MIN)
		.sort((a, b) => b.books.length - a.books.length || a.topic.title.localeCompare(b.topic.title));
	while (chosen.length < ROW_TOPICS.length && rest.length) chosen.push(rest.shift()!.topic.slug);

	for (const slug of chosen) {
		const e = topics.get(slug)!;
		rows.push({ topic: e.topic, count: e.books.length, books: e.books.slice(0, ROW_MAX) });
	}
	return rows;
}
