import { getQuoteTopicPage, listQuoteTopics } from '$lib/library-public';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// Only themes deep enough to have earned a page. The threshold lives on the
// server, so the build cannot render a thin theme — and the sitemap reads the
// same list, so it cannot advertise one either.
export const entries: EntryGenerator = async () => {
	try {
		return (await listQuoteTopics()).map((tp) => ({ topic: tp.slug }));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params, fetch }) => ({
	page: await orNotFound(() => getQuoteTopicPage(params.topic, fetch))
});
