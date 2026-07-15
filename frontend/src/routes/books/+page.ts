import { listBooks, type BookSummary } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

/**
 * Await the shelf so the page prerenders with real content (and its JSON-LD),
 * folding a fetch failure into `{ loadError: true }` so a client-side navigation
 * to a down API shows a retry panel instead of the error route.
 *
 * Prerender refresh 2026-07-15: force an ochorus-web rebuild after the api went
 * live with the 4 new Spanish (es) books, so the localized /es/books index and
 * the /es/books/<slug> pages re-crawl and bake with the new titles.
 *
 * Prerender refresh 2026-07-15 (lg/sw): same again after the Luganda + Swahili
 * translations went live, so /lg/books and /sw/books (and their /<slug> pages)
 * re-crawl and bake with the new titles.
 */
export const load: PageLoad = async () => {
	try {
		return { books: await listBooks(getLang()), loadError: false };
	} catch {
		return { books: [] as BookSummary[], loadError: true };
	}
};
