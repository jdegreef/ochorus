import { listQuoteTopics } from '$lib/library-public';
import { loadShelf } from '$lib/loadShelf';
import type { PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// English-only, like the quotes it indexes: the sentences are lifted from the
// English works. The list comes from the same endpoint the topic-page entry
// generator and the sitemap read, so all three advertise exactly the themes deep
// enough to have earned a page.
export const load: PageLoad = async () => {
	const { items, loadError } = await loadShelf(listQuoteTopics());
	return { topics: items, loadError };
};
