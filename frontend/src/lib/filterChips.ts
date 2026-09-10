/**
 * Active-filter chips for the browse shelves — the removable pills `FilterSummary`
 * renders. The query and the topic are the two filters no `<select>` reads back
 * (a book/length/source control shows its own value), so every shelf that has
 * them builds the same two chips; those live here rather than copy-pasted per
 * page. A shelf's own filters (a book, a length, a source) stay inline — their
 * label resolution is shelf-specific.
 */

/** One removable filter. `kind` is the stable `{#each}` key (labels can collide —
 *  a topic named the same as a book). */
export type FilterChip = { kind: string; label: string; onRemove: () => void };

/** The free-text query as a chip, or null when the box is empty. */
export function queryChip(filters: { values: { q: string } }): FilterChip | null {
	const q = filters.values.q.trim();
	return q ? { kind: 'q', label: `“${q}”`, onRemove: () => (filters.values.q = '') } : null;
}

/** The active topic as a chip, resolving its slug to the title on the shelf, or
 *  null when no topic is selected. */
export function topicChip(
	filters: { values: { topic: string } },
	topics: { slug: string; title: string }[]
): FilterChip | null {
	const slug = filters.values.topic;
	if (!slug) return null;
	return {
		kind: 'topic',
		label: topics.find((t) => t.slug === slug)?.title ?? slug,
		onRemove: () => (filters.values.topic = '')
	};
}
