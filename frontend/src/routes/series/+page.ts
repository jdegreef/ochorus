import { listSeries } from '$lib/library-public';
import { loadShelf } from '$lib/loadShelf';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

// The Book Series index — a browse shelf on the Topics model. Prerenders to
// /series/index.html like /originals, so its links carry the slash (href.ts
// SLASHED_PAGES) and the crawler reaches every localized copy from the footer.
export const prerender = true;
export const trailingSlash = 'always';

export const load: PageLoad = async ({ fetch }) => {
	const { items, loadError } = await loadShelf(listSeries(getLang(), fetch));
	return { series: items, loadError };
};
