/**
 * Move a node to the end of `<body>` for as long as it is mounted.
 *
 * For fixed-position overlays: an ancestor with a `transform`, `filter` or
 * `backdrop-filter` becomes the containing block for `position: fixed`, so an
 * overlay rendered inside one is laid out against that ancestor rather than the
 * viewport (and trapped in its stacking context). `.page-col` is centred with a
 * transform and the reader's bars carry a backdrop-filter, so without this every
 * caller had to remember to render its drawer outside them.
 *
 * SAFE ONLY ON A BLOCK'S SOLE ROOT NODE. Svelte 5 tears a block down by
 * removing the DOM range from its first node to its last, walking
 * `nextSibling`. If the moved node is one of several siblings in an `{#if}`,
 * that walk starts or ends in `<body>` and removes the wrong nodes. As the only
 * root (start === end) it is removed wherever it now lives. And when an
 * ANCESTOR block is torn down instead, Svelte removes the ancestor's range —
 * which no longer contains this node — so `destroy` removes it here, or it
 * would leak in `<body>` for good.
 */
export function portal(node: HTMLElement) {
	document.body.appendChild(node);
	return {
		destroy() {
			node.remove();
		}
	};
}
