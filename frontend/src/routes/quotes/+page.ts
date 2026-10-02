import { listFeaturedQuotes, listQuoteAuthors, listQuoteTopics } from '$lib/library-public';
import { loadShelf } from '$lib/loadShelf';
import type { PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// English-only, like the author quote pages it links to: the quotations are
// lifted from the English works, so there is no translated index to serve. The
// list comes from the same endpoint the author-page entry generator and the
// sitemap read, so all three advertise exactly the reviewed set.
//
// The quote themes ride along for the topic chips — the page's second way in.
// A failed topic fetch only hides the chips; the authors decide the error state.
export const load: PageLoad = async ({ fetch }) => {
	const [authors, topics, featured] = await Promise.all([
		loadShelf(listQuoteAuthors(fetch)),
		loadShelf(listQuoteTopics(fetch)),
		// The lead quotation's pool; a failed fetch just leaves the page without it.
		loadShelf(listFeaturedQuotes(fetch))
	]);
	return {
		authors: authors.items,
		loadError: authors.loadError,
		topics: topics.items,
		featured: featured.items
	};
};
