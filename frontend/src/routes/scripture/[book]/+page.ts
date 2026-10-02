import { getScriptureBook, listScripturePages } from '$lib/library-public';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// One entry per Bible book with at least one chapter page — the rule the API's
// ScriptureBookView enforces and the sitemap section reads, from the SAME list,
// so a book page cannot be advertised without being built.
export const entries: EntryGenerator = async () => {
	try {
		const pages = await listScripturePages();
		return [...new Set(pages.filter((p) => p.verse === null).map((p) => p.book))].map((book) => ({
			book
		}));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params, fetch }) => ({
	page: await orNotFound(() => getScriptureBook(params.book, fetch))
});
