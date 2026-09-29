import { tick } from 'svelte';
import type { Snapshot } from '@sveltejs/kit';

/**
 * "Show more" paging for a flat shelf: the first `page` items, then another
 * page per tap. The count belongs to one view — `key()` names it (the filters
 * and sort, spelled out) — so a new filter starts over at one page. Kept as
 * (key, count) rather than reset in an effect: an $effect that writes state is
 * a $derived in disguise (frontend/CLAUDE.md). Call during component setup.
 *
 * `capture()` / `restore()` are for the route's snapshot — see `pagedSnapshot`
 * below. A restored count only applies while its view key still matches.
 */
export type PagerState = { key: string; count: number };

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
		},
		/** Show at least through `index` (a jump to an item not painted yet). */
		reveal(index: number) {
			const need = Math.ceil((index + 1) / page) * page;
			if (need > limit) expanded = { key: key(), count: need };
		},
		capture(): PagerState {
			return { key: key(), count: limit };
		},
		restore(s: PagerState | undefined) {
			if (s) expanded = s;
		}
	};
}
export type Pager = ReturnType<typeof pager>;

/**
 * A route's SvelteKit `snapshot` for a paged shelf, so Back from an item lands
 * where you were. Without it the shelf re-mounted at one page and the restored
 * scroll position — past that page's end — clamped to the bottom.
 *
 * It carries its own scroll position because SvelteKit restores a snapshot
 * AFTER it restores scroll (client.js: scrollTo, then restore_snapshot on
 * popstate): by then the scroll has clamped to the short page, and the browser's
 * scroll anchoring rides the footer down as the restored rows render. So:
 * restore the count, wait for the rows, then put the scroll back. A shelf
 * component exposes its pager as `export const pages`.
 */
export function pagedSnapshot(
	pages: () =>
		| { capture(): PagerState | undefined; restore(s: PagerState | undefined): void }
		| undefined
): Snapshot<{ paging: PagerState | undefined; y: number }> {
	return {
		capture: () => ({ paging: pages()?.capture(), y: scrollY }),
		restore: async ({ paging, y }) => {
			pages()?.restore(paging);
			await tick();
			// …and one frame for layout, so the page is its full height again —
			// unless the reader has already navigated on.
			const here = location.href;
			requestAnimationFrame(() => {
				if (location.href === here) scrollTo(0, y);
			});
		}
	};
}
