import { getAudienceShelf, getBookGuide, guideSlugs } from '$lib/library-public';
import { getLang } from '$lib/lang.svelte';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

// A printable leader's guide for a young-reader edition. Prerendered like the
// book page; the English guides are seeded from the two hubs' `guides` shelves,
// and a localized guide is reached by the crawler through the "Leader's guide"
// link on its localized book page (shown only when that edition has one).
export const prerender = true;
export const trailingSlash = 'always';

export const entries: EntryGenerator = async () => {
	const shelves = await Promise.all([
		getAudienceShelf('young_readers', 'en'),
		getAudienceShelf('teens', 'en')
	]);
	return guideSlugs(shelves).map((slug) => ({ slug }));
};

export const load: PageLoad = async ({ params, fetch }) => {
	// No English fallback: a language with no guide is a 404, as the API says.
	const guide = await orNotFound(() => getBookGuide(params.slug, getLang(), fetch));
	return { guide };
};
