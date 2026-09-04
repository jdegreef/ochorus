import { listScripturePages } from '$lib/library-public';
import { loadShelf } from '$lib/loadShelf';
import type { PageLoad } from './$types';

// The hub for the scripture graph, and the reason its pages are not orphans: a
// page reachable only from the sitemap tells search engines you do not value it
// either. From here every chapter page is one click, every verse page two.
export const prerender = true;
export const trailingSlash = 'always';

export const load: PageLoad = async () => {
	// A lagging API is REPORTED (loadShelf), not silently baked as an empty
	// index that reads "still being built": the page shows Try again instead,
	// and a later rebuild picks the pages up. Same treatment as /topics.
	const { items, loadError } = await loadShelf(listScripturePages());
	return { pages: items, loadError };
};
