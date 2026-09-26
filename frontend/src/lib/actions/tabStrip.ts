/**
 * A horizontally scrolling row of section tabs (the book and author pages'
 * sticky jump-navs). Pair with the `.tab-strip` class in app.css.
 *
 * - Keeps the active tab in view: on a phone the row holds two or three of
 *   its tabs, and it used to highlight one it had scrolled out of sight. Only
 *   the strip scrolls — `scrollIntoView` would also move the page, fighting
 *   the reader's own scroll and a smooth jump already in flight.
 * - Marks which ends have tabs hidden past them (`more-start` / `more-end`),
 *   so the CSS fades an edge only when something is really there. Observes
 *   the tabs as well as the strip: a font load or a new section changes their
 *   widths without resizing the strip.
 *
 *   <ul class="tab-strip" use:tabStrip={spy.active}>…<a href="#id">…
 */
export function tabStrip(node: HTMLElement, active: string | null | undefined) {
	function syncEdges() {
		// |scrollLeft|: RTL scrolls negative.
		const x = Math.abs(node.scrollLeft);
		node.classList.toggle('more-start', x > 1);
		node.classList.toggle('more-end', x + node.clientWidth < node.scrollWidth - 1);
	}
	function reveal(id: string | null | undefined) {
		const link = id ? node.querySelector<HTMLElement>(`[href="#${CSS.escape(id)}"]`) : null;
		if (!link) return;
		const strip = node.getBoundingClientRect();
		const tab = link.getBoundingClientRect();
		// Physical deltas, so the same arithmetic holds under RTL.
		const pad = 16;
		if (tab.left < strip.left) node.scrollBy({ left: tab.left - strip.left - pad });
		else if (tab.right > strip.right) node.scrollBy({ left: tab.right - strip.right + pad });
	}

	const ro = new ResizeObserver(syncEdges);
	ro.observe(node);
	for (const child of node.children) ro.observe(child);
	// Tabs rendered later (a client nav to a book with other sections) join
	// the observer too.
	const mo = new MutationObserver((records) => {
		for (const r of records) for (const n of r.addedNodes) if (n instanceof Element) ro.observe(n);
		syncEdges();
	});
	mo.observe(node, { childList: true });
	node.addEventListener('scroll', syncEdges, { passive: true });
	syncEdges();
	reveal(active);

	return {
		update(next: string | null | undefined) {
			reveal(next);
			syncEdges();
		},
		destroy() {
			ro.disconnect();
			mo.disconnect();
			node.removeEventListener('scroll', syncEdges);
		}
	};
}
