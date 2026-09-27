import { bookmarks } from '$lib/bookmarks.svelte';
import type { WorkKind } from '$lib/reading-schema';

/**
 * The Bookmark control of a single-document Reader surface — a sermon or a
 * biography. Each is one "chapter" (order 1), so a bookmark is a paragraph:
 * the one at the top of the screen — so the control belongs in a bar that
 * stays on screen while reading. Written once; it was copied line for line
 * into each page.
 *
 * `topIndex` is a DOM measurement, so it is re-read when the reader has moved
 * — `frac` changes on Reader's throttled scroll pass, which is exactly when
 * the answer can have changed — rather than derived. Reader's own
 * `topVisibleIndex` is the measure, so the bookmark and the resume point agree
 * on which paragraph "the top" is.
 *
 * Call during component setup (it owns effects), with getters, so a
 * client-side hop to another work re-reads them.
 */
export function readerBookmark(o: {
	kind: WorkKind;
	slug: () => string;
	/** The work's title, stored with the bookmark for the Notebook. */
	title: () => string;
	reader: () => { topVisibleIndex(): number } | undefined;
	body: () => HTMLElement | undefined;
	frac: () => number;
}) {
	const ORDER = 1;
	let topIndex = $state(0);

	$effect(() => {
		void o.frac();
		void o.slug();
		topIndex = o.reader()?.topVisibleIndex() ?? 0;
	});
	$effect(() => {
		bookmarks.load(o.kind, o.slug());
	});

	return {
		/** Whether the paragraph at the top of the screen is bookmarked. */
		get current(): boolean {
			return bookmarks.has(ORDER, topIndex);
		},
		/** Bookmark (or un-bookmark) the paragraph at the top of the screen. */
		toggle() {
			const body = o.body();
			if (!body) return;
			const p = o.reader()?.topVisibleIndex() ?? 0;
			const el = body.children[p] as HTMLElement | undefined;
			const snippet = (el?.innerText ?? '').trim().replace(/\s+/g, ' ').slice(0, 90);
			bookmarks.toggle(ORDER, p, snippet, o.title());
			topIndex = p;
		}
	};
}
