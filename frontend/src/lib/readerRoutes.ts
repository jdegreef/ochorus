/**
 * The two reading surfaces, by SvelteKit route id.
 *
 * A chapter and a sermon are the pages where the text itself is the product,
 * and they behave differently from every browse surface in two ways that both
 * need this list:
 *
 * 1. They pin their OWN bar to the top, so the global nav goes static
 *    (`.appnav-static`).
 * 2. Their column is governed by `--reading-measure` (the `A a` popover's
 *    width control), NOT by the `pageWidth` store — so the quick-settings
 *    **Page width** stepper has nothing to act on and hides itself there.
 *
 * That second one is why this moved out of the layout. The stepper was still
 * rendered on both pages: it opened, it stored a new value, and the article
 * never moved — a control six pixels from the one that actually resizes the
 * text, quietly doing nothing. Two components now have to agree about what
 * counts as a reading surface, and a route id repeated in two files is a route
 * id that gets updated in one.
 *
 * Adding a third reading surface? Add it here and both behaviours follow.
 */
export const READER_ROUTE_IDS = ['/books/[slug]/[order]', '/sermons/[slug]'] as const;

/** Whether a route id (as given by `$page.route.id`) is a reading surface. */
export function isReaderRoute(routeId: string | null | undefined): boolean {
	return !!routeId && (READER_ROUTE_IDS as readonly string[]).includes(routeId);
}
