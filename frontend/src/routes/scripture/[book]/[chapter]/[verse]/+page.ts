import { getScripturePage, listScripturePages } from '$lib/library-public';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// Verse pages clear a HIGHER floor than chapter pages (see scripture_graph):
// a chapter page aggregates every verse under it and stays substantial where a
// verse page would not.
export const entries: EntryGenerator = async () => {
	try {
		const pages = await listScripturePages();
		return pages
			.filter((p) => p.verse !== null)
			.map((p) => ({
				book: p.book,
				chapter: String(p.chapter),
				verse: String(p.verse)
			}));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params, fetch }) => ({
	page: await orNotFound(() =>
		getScripturePage(params.book, Number(params.chapter), Number(params.verse), fetch)
	)
});
