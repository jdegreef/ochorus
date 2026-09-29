/**
 * "Show more" paging for a flat shelf: the first `page` items, then another
 * page per tap. The count belongs to one view — `key()` names it (the filters
 * and sort, spelled out) — so a new filter starts over at one page. Kept as
 * (key, count) rather than reset in an effect: an $effect that writes state is
 * a $derived in disguise (frontend/CLAUDE.md). Call during component setup.
 */
export function pager<T>(items: () => T[], key: () => string, page = 24) {
	let expanded = $state({ key: '', count: page });
	const limit = $derived(expanded.key === key() ? expanded.count : page);
	const visible = $derived(items().slice(0, limit));
	const remaining = $derived(items().length - visible.length);
	return {
		get visible() {
			return visible;
		},
		get remaining() {
			return remaining;
		},
		/** How many the next tap adds — the button's number. */
		get next() {
			return Math.min(page, remaining);
		},
		more() {
			expanded = { key: key(), count: limit + page };
		}
	};
}
export type Pager = ReturnType<typeof pager>;
