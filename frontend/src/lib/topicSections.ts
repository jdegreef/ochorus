export type TopicSectionKind = 'books' | 'sermons' | 'articles';

/**
 * The order the topic page shows its content sections — books, sermons,
 * articles — dropping any that are empty.
 *
 * Books and sermons lead with whichever the topic is mostly made of, so a
 * sermon-dominated topic (The Gospel Call: 4 books, 25 sermons; Christ & the
 * Cross: sermons only) leads with its sermons instead of burying them under a
 * short books grid, while a book-dominated one (the Puritans, On Prayer) leads
 * with books. Ties keep books before sermons.
 *
 * Articles always come LAST, whatever their count. They used to join the
 * count race, and once the articles push outgrew the shelves (On Prayer: 10
 * books, 17 articles; Enduring Classics: 8 books, 61 articles) eight topics —
 * "Books on Prayer" among them — opened on a wall of study guides with the
 * library itself screens below. The articles are companions to the classics,
 * not the shelf.
 *
 * Adapt-from-data, applied to every topic — the same principle as the by-author
 * book grouping — not a per-topic layout.
 */
const CANON: readonly TopicSectionKind[] = ['books', 'sermons', 'articles'];

export function topicSectionOrder(counts: Record<TopicSectionKind, number>): TopicSectionKind[] {
	const shelves = (['books', 'sermons'] as const)
		.filter((kind) => counts[kind] > 0)
		.sort((a, b) => counts[b] - counts[a] || CANON.indexOf(a) - CANON.indexOf(b));
	return counts.articles > 0 ? [...shelves, 'articles'] : [...shelves];
}
