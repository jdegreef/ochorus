import { listQuoteAuthors } from '$lib/library-public';
import { loadShelf } from '$lib/loadShelf';
import type { PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// English-only, like the author quote pages it links to: the quotations are
// lifted from the English works, so there is no translated index to serve. The
// list comes from the same endpoint the author-page entry generator and the
// sitemap read, so all three advertise exactly the reviewed set.
export const load: PageLoad = async ({ fetch }) => {
	const { items, loadError } = await loadShelf(listQuoteAuthors(fetch));
	return { authors: items, loadError };
};
