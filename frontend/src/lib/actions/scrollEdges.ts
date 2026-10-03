/**
 * Marks which ends of a sideways-scrolling row have content hidden past them
 * (`more-start` / `more-end`), so the CSS fades an edge only when something
 * is really there. Used by `.tab-strip` (via `tabStrip`), `.chip-scroller`
 * and `.cover-rail` — a static end-edge mask dimmed the last chip even when
 * scrolled to the end, and never faded the start edge at all. Observes the
 * children as well as the row: a font load or a late-rendered item changes
 * their widths without resizing the row.
 *
 *   <div class="chip-scroller" use:scrollEdges>…
 */
export function scrollEdges(node: HTMLElement) {
	function sync() {
		// |scrollLeft|: RTL scrolls negative.
		const x = Math.abs(node.scrollLeft);
		node.classList.toggle('more-start', x > 1);
		node.classList.toggle('more-end', x + node.clientWidth < node.scrollWidth - 1);
	}

	const ro = new ResizeObserver(sync);
	ro.observe(node);
	for (const child of node.children) ro.observe(child);
	// Items rendered later (a client nav, a filter) join the observer too…
	const mo = new MutationObserver((records) => {
		for (const r of records) {
			for (const n of r.addedNodes) if (n instanceof Element) ro.observe(n);
			// …and leave with it: a filtered row re-renders its children, and
			// an observed detached node is held until the row is destroyed.
			for (const n of r.removedNodes) if (n instanceof Element) ro.unobserve(n);
		}
		sync();
	});
	mo.observe(node, { childList: true });
	node.addEventListener('scroll', sync, { passive: true });
	sync();

	return {
		/** Re-measure now (after the caller scrolled the row itself). */
		sync,
		destroy() {
			ro.disconnect();
			mo.disconnect();
			node.removeEventListener('scroll', sync);
		}
	};
}

/** Scroll `item` into view inside the row `strip` — the row only, never the
 *  page (`scrollIntoView` would also move the page, fighting the reader's own
 *  scroll, a `#hash` landing, or a smooth jump already in flight). */
export function revealInStrip(strip: HTMLElement, item: HTMLElement | null | undefined, pad = 16) {
	if (!item) return;
	const s = strip.getBoundingClientRect();
	const r = item.getBoundingClientRect();
	// Physical deltas, so the same arithmetic holds under RTL.
	if (r.left < s.left) strip.scrollBy({ left: r.left - s.left - pad });
	else if (r.right > s.right) strip.scrollBy({ left: r.right - s.right + pad });
}
