/**
 * Repaint the page's look — a theme or a palette — as a short crossfade
 * rather than a cut, so choosing Sepia or Cathedral feels like turning up a
 * lamp. Uses the View Transitions API where the browser has it; elsewhere, and
 * for a reader who asks for less motion or a tab nobody is looking at, the
 * change simply happens. `change` must apply the new look synchronously
 * (setting `data-theme` / `data-palette`), which is all the API needs to
 * snapshot the after-state. The fade's timing is `::view-transition-*(root)`
 * in app.css.
 *
 * Import-free on purpose: theme.svelte.ts loads on every page, and
 * `$lib/reading`'s prefersReducedMotion would bring the reader's modules with it.
 */
export function crossfade(change: () => void): void {
	if (!canViewTransition()) {
		change();
		return;
	}
	document.startViewTransition(change);
}

/** Whether a view transition may run now: the browser has the API, the tab is
 *  being looked at, and the reader hasn't asked for less motion. The one rule
 *  for the site's transitions (this crossfade, $lib/coverFlight). */
export function canViewTransition(): boolean {
	const doc = typeof document === 'undefined' ? null : document;
	return (
		typeof doc?.startViewTransition === 'function' &&
		doc.visibilityState === 'visible' &&
		!globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches
	);
}
