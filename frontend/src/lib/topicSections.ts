export type TopicSectionKind = 'books' | 'sermons' | 'articles';

/**
 * The order the topic page shows its content sections — books, sermons,
 * articles — leading with the type the topic is mostly made of, and dropping
 * any that are empty.
 *
 * So a sermon-dominated topic (The Gospel Call: 4 books, 25 sermons; Christ &
 * the Cross: sermons only) leads with its sermons instead of burying them under
 * a short books grid, while a book-dominated topic (the Puritans, On Prayer)
 * still leads with books. Ties keep the canonical books → sermons → articles
 * order, so a balanced topic reads in the familiar sequence.
 *
 * Adapt-from-data, applied to every topic — the same principle as the by-author
 * book grouping — not a per-topic layout.
 */
const CANON: readonly TopicSectionKind[] = ['books', 'sermons', 'articles'];

export function topicSectionOrder(counts: Record<TopicSectionKind, number>): TopicSectionKind[] {
	return CANON.filter((kind) => counts[kind] > 0).sort(
		(a, b) => counts[b] - counts[a] || CANON.indexOf(a) - CANON.indexOf(b)
	);
}
