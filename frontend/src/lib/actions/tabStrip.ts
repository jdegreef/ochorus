import { revealInStrip, scrollEdges } from './scrollEdges';

/**
 * A horizontally scrolling row of section tabs (the book and author pages'
 * sticky jump-navs). Pair with the `.tab-strip` class in app.css.
 *
 * - Keeps the active tab in view: on a phone the row holds two or three of
 *   its tabs, and it used to highlight one it had scrolled out of sight. Only
 *   the strip scrolls (`revealInStrip`). Pass the active section id for a
 *   jump-nav, or nothing for a row of route tabs (`.is-active`).
 * - Marks which ends have tabs hidden past them (`scrollEdges`), so the CSS
 *   fades an edge only when something is really there.
 *
 *   <ul class="tab-strip" use:tabStrip={spy.active}>…<a href="#id">…
 */
export function tabStrip(node: HTMLElement, active: string | null | undefined) {
	const edges = scrollEdges(node);
	// A jump-nav names its active tab by section id; a route tab row (no id)
	// marks it with `.is-active` / aria-current, so that is what's revealed.
	function reveal(id: string | null | undefined) {
		revealInStrip(
			node,
			node.querySelector<HTMLElement>(
				id ? `[href="#${CSS.escape(id)}"]` : '.is-active, [aria-current="page"]'
			)
		);
	}
	reveal(active);

	return {
		update(next: string | null | undefined) {
			reveal(next);
			edges.sync();
		},
		destroy: edges.destroy
	};
}
