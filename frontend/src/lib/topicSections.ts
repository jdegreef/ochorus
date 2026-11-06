export type TopicSectionKind = 'books' | 'sermons' | 'articles';

/**
 * The topic page's tabs — Books · Sermons · Articles — in that fixed order,
 * dropping any that are empty. The first one is the tab the page opens on.
 *
 * Books always lead (design review #16). Books are the heart of the library,
 * and the page used to open a sermon-heavy shelf (On Prayer: 17 books, 24
 * sermons) on two dozen sermon cards before a single cover. Each kind now sits
 * in its own tab with its count, so a reader who came for sermons is one tap
 * away from them — which retires the old rule that raced books against
 * sermons by count to decide which led.
 *
 * Articles always come last: they are companions to the classics, not the
 * shelf (eight topics once opened on a wall of study guides). A topic with no
 * books opens on its sermons (Christ & the Cross) — the first NON-EMPTY kind
 * leads.
 */
const CANON: readonly TopicSectionKind[] = ['books', 'sermons', 'articles'];

export function topicSectionOrder(counts: Record<TopicSectionKind, number>): TopicSectionKind[] {
	return CANON.filter((kind) => counts[kind] > 0);
}

/**
 * Whether a topic page leads with a "Book Series" row: when at least half its
 * books are series volumes. For Young Readers (16 of 19) does; Deeper Life,
 * with two Key Teachings books among eight, is better met as books than as a
 * half-empty series card.
 */
export function topicLeadsWithSeries(books: { series?: unknown }[]): boolean {
	const inSeries = books.filter((b) => b.series).length;
	return inSeries > 0 && inSeries * 2 >= books.length;
}
