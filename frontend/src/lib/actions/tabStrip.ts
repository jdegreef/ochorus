import { revealInStrip, scrollEdges } from './scrollEdges';

/**
 * A horizontally scrolling row of section tabs (the book and author pages'
 * sticky jump-navs). Pair with the `.tab-strip` class in app.css.
 *
 * - Keeps the active tab in view: on a phone the row holds two or three of
 *   its tabs, and it used to highlight one it had scrolled out of sight. Only
 *   the strip scrolls (`revealInStrip`). Pass the active section id for a
 *   jump-nav (`href="#id"`) or an in-page tab list (`aria-controls="id"`, the
 *   topic page), or nothing for a row of route tabs (`.is-active`).
 * - Marks which ends have tabs hidden past them (`scrollEdges`), so the CSS
 *   fades an edge only when something is really there.
 *
 *   <ul class="tab-strip" use:tabStrip={spy.active}>…<a href="#id">…
 */
export function tabStrip(node: HTMLElement, active: string | null | undefined) {
	const edges = scrollEdges(node);
	// A jump-nav or tab list names its active tab by section/panel id; a route
	// tab row (no id) marks it with `.is-active` / aria-current, so that is
	// what's revealed. A row of buttons with no `#id` link or panel to find
	// (Search's kind tabs pass their selection only so `update` runs when it
	// changes) falls back to the marked tab too.
	function reveal(id: string | null | undefined) {
		revealInStrip(
			node,
			(id
				? node.querySelector<HTMLElement>(
						`[href="#${CSS.escape(id)}"], [aria-controls="${CSS.escape(id)}"]`
					)
				: null) ?? node.querySelector<HTMLElement>('.is-active, [aria-current="page"]')
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
