import { listBooks, type BookSummary } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

/**
 * Await the shelf so the page prerenders with real content (and its JSON-LD),
 * folding a fetch failure into `{ loadError: true }` so a client-side navigation
 * to a down API shows a retry panel instead of the error route.
 */
export const load: PageLoad = async () => {
	try {
		return { books: await listBooks(getLang()), loadError: false };
	} catch {
		return { books: [] as BookSummary[], loadError: true };
	}
};
