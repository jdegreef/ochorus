import { getQuoteAuthorTopicPage, listQuoteTopicPages } from '$lib/library-public';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// Only (author, theme) pairs deep enough to have earned a page. The threshold
// lives on the server, so the build cannot render a thin pair — and the sitemap
// reads the same list, so it cannot advertise one either.
export const entries: EntryGenerator = async () => {
	try {
		return (await listQuoteTopicPages()).map((p) => ({ author: p.author, topic: p.topic }));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params, fetch }) => ({
	page: await orNotFound(() => getQuoteAuthorTopicPage(params.author, params.topic, fetch))
});
