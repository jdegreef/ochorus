/**
 * Publish a node's rendered height (border box, so its top rule counts) as a
 * CSS custom property on the document root, for as long as the node is
 * mounted — so fixed chrome elsewhere can clear a bar docked at the bottom
 * (the PWA toasts read ReadBar, the book and plan pages' phone read bar, as
 * --dockbar-h). Measured, not assumed: the height moves with the type scale. Removed on destroy, so
 * a bar inside an {#if} leaves no stale clearance behind when it goes.
 */
export function publishHeight(node: HTMLElement, name: string) {
	const root = document.documentElement;
	const ro = new ResizeObserver(() =>
		root.style.setProperty(name, `${Math.round(node.getBoundingClientRect().height)}px`)
	);
	ro.observe(node);
	return {
		destroy() {
			ro.disconnect();
			root.style.removeProperty(name);
		}
	};
}
