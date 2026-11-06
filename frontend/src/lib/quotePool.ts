import { listFeaturedQuotes, type SavedQuote } from '$lib/library-public';

/**
 * The featured quotations — short, reviewed, writers interleaved — fetched
 * once per page session and shared: the home page's quote of the day
 * (HomeQuote) and any other surface that shows one draw from
 * the same pool. A failed fetch isn't kept, so the next ask retries.
 */
let pending: Promise<SavedQuote[]> | null = null;
export function featuredPool(): Promise<SavedQuote[]> {
	pending ??= listFeaturedQuotes().catch((e) => {
		pending = null;
		throw e;
	});
	return pending;
}
