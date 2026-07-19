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
 *
 * Prerender refresh 2026-07-15 (classic authors): force an ochorus-web rebuild
 * after the api went live with 11 new public-domain works (Bunyan, Watson,
 * Baxter, Edwards, Whitefield, Wesley), so the /books index, the new
 * /books/<slug> and /authors/<slug> pages, and the sitemap re-crawl and bake.
 *
 * Prerender refresh 2026-07-17 (queue job #169): same again after the Luganda
 * edition of Clothed with Strength and Dignity went live, so /lg/books and
 * its /books/<slug> pages re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-17 (queue job #170): same again after the Luganda
 * edition of The Key in My Hand (Ekisumuluzo Ekiri mu Mukono Gwange, PR #174)
 * went live, so the /lg/books pages re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-17 (queue job #179): same again after the Luganda
 * edition of Godliness (Okutya Katonda, PR #184) went live, so the /lg/books
 * pages re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-19 (queue job #199): same again after the Spanish
 * edition of Prayer – The Pulse of Life (Oración – El Pulso de la Vida, PR
 * #226) went live, so the /es/books index and its /books/<slug> pages re-crawl
 * and bake with the new title.
 */
export const load: PageLoad = async () => {
	try {
		return { books: await listBooks(getLang()), loadError: false };
	} catch {
		return { books: [] as BookSummary[], loadError: true };
	}
};
