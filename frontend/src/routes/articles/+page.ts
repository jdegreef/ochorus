import { listArticles } from '$lib/library-public';
import { loadShelf } from '$lib/loadShelf';
import type { PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// English-only for now — articles are original site writing, not yet
// translated. The list comes from the same endpoint the [slug] entry generator
// and the sitemap read, so all three advertise exactly the same set. A lagging
// API is REPORTED (loadShelf) so the page can offer Try again, rather than
// baking a false "no articles yet".
export const load: PageLoad = async () => {
	const { items, loadError } = await loadShelf(listArticles('en'));
	return { articles: items, loadError };
};
