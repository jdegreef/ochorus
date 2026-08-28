import { getQuotePage, listQuoteAuthors } from '$lib/library-public';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// Only authors whose quotations a person has REVIEWED. The gate lives on the
// server, so the build cannot render a page the review has not opened — and the
// sitemap reads the same list, so it cannot advertise one either.
export const entries: EntryGenerator = async () => {
	try {
		return (await listQuoteAuthors()).map((author) => ({ author }));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params }) => ({
	page: await orNotFound(() => getQuotePage(params.author))
});
