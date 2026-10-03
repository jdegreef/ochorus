import { revealInStrip, scrollEdges } from './scrollEdges';

/**
 * A horizontally scrolling row of section tabs (the book and author pages'
 * sticky jump-navs). Pair with the `.tab-strip` class in app.css.
 *
 * - Keeps the active tab in view: on a phone the row holds two or three of
 *   its tabs, and it used to highlight one it had scrolled out of sight. Only
 *   the strip scrolls (`revealInStrip`).
 * - Marks which ends have tabs hidden past them (`scrollEdges`), so the CSS
 *   fades an edge only when something is really there.
 *
 *   <ul class="tab-strip" use:tabStrip={spy.active}>…<a href="#id">…
 */
export function tabStrip(node: HTMLElement, active: string | null | undefined) {
	const edges = scrollEdges(node);
	function reveal(id: string | null | undefined) {
		revealInStrip(node, id ? node.querySelector<HTMLElement>(`[href="#${CSS.escape(id)}"]`) : null);
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
