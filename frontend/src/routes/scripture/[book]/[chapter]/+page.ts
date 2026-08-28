import { getScripturePage, listScripturePages } from '$lib/library-public';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// One entry per Bible chapter the API says has earned a page. The floor lives
// server-side in scripture_graph.qualifying_pages, and the sitemap section reads
// the SAME list — so a page cannot be advertised without being built.
export const entries: EntryGenerator = async () => {
	try {
		const pages = await listScripturePages();
		return pages
			.filter((p) => p.verse === null)
			.map((p) => ({ book: p.book, chapter: String(p.chapter) }));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params }) => ({
	page: await orNotFound(() => getScripturePage(params.book, Number(params.chapter)))
});
