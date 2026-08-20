/**
 * Fetch a browse shelf, and report a failure instead of pretending to be empty.
 *
 * Books, Sermons, Topics and Plans each wrote the same try/catch, and three of
 * them threw the error away — so a page whose API call failed said "no plans
 * available in this language yet", which is a claim about the library rather
 * than a report of what happened. A reader who saw it had no reason to retry.
 *
 * The failure is still caught rather than thrown: these pages are prerendered
 * and the API can deploy alongside the web build, so a lagging endpoint must
 * not fail the build. What changes is that it is REPORTED — `loadError` reaches
 * the page, which shows the panel with Try again, and that button re-runs this
 * load against the live API. So a build that bakes the error still recovers on
 * the first visit, and nothing silently ships an empty shelf.
 *
 * (The home page's own `shelf()` in `routes/+page.ts` is deliberately different:
 * it throws during the build. Its front-page shelf has no error state of its
 * own — the section simply hides when empty — so for that one page a failure
 * has to be loud where a human will see it.)
 */
export async function loadShelf<T>(
	pending: Promise<T[]>
): Promise<{ items: T[]; loadError: boolean }> {
	try {
		return { items: await pending, loadError: false };
	} catch {
		return { items: [], loadError: true };
	}
}
