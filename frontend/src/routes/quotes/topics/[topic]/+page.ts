import { getQuoteTopicPage, listQuoteTopics, listTopics } from '$lib/library-public';
import { topicsForTheme } from '$lib/topicQuotes';
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

export const load: PageLoad = async ({ params, fetch }) => {
	// The book-and-sermon shelves that read as this theme ($lib/topicQuotes),
	// for the way back to the works. Global fetch, so the shelf list is not
	// inlined; a failure just drops the links.
	const [page, shelves] = await Promise.all([
		orNotFound(() => getQuoteTopicPage(params.topic, fetch)),
		listTopics('en')
			.then((all) => topicsForTheme(params.topic, all).map(({ slug, title }) => ({ slug, title })))
			.catch(() => [])
	]);
	return { page, shelves };
};
