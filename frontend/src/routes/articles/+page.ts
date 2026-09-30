import { listArticles } from '$lib/library-public';
import { loadShelf } from '$lib/loadShelf';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// The Articles hub in the reader's language: each locale lists its OWN articles
// (per-language rows, no English fallback — a language with none shows the
// empty state and is noindexed). The build seeds `/<l>/articles/` for every
// locale (svelte.config.js), and a translated hub lists every one of its
// articles unpaged, so it is the crawl's guaranteed way to each translated
// article — the [slug] entry generator only emits English params. The sitemap
// advertises the same per-locale set.
export const load: PageLoad = async ({ fetch }) => {
	const { items, loadError } = await loadShelf(listArticles(getLang(), fetch));
	return { articles: items, loadError };
};
