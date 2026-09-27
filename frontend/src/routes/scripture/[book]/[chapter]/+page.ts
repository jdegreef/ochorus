import {
	getScripturePage,
	listScripturePages,
	type ScriptureNeighbour
} from '$lib/library-public';
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

// Prev/next among the CHAPTER pages, in canonical Bible order — so a reader (and
// a crawler) can walk the reverse index instead of returning to the hub each
// time. The API names the adjacent QUALIFYING pages (not chapter ± 1, which may
// never have been built) in the page's own payload.
type ScriptureNav = { href: string; label: string } | null;

const nav = (p: ScriptureNeighbour | null | undefined): ScriptureNav =>
	p ? { href: `/scripture/${p.book}/${p.chapter}/`, label: `${p.book_title} ${p.chapter}` } : null;

export const load: PageLoad = async ({ params, fetch }) => {
	const chapter = Number(params.chapter);
	const page = await orNotFound(() => getScripturePage(params.book, chapter, undefined, fetch));
	if (page.prev !== undefined) return { page, prev: nav(page.prev), next: nav(page.next) };
	// An API from before prev/next were in the payload (a web build racing the
	// API's deploy): find them in the page list, as this page used to. Global
	// fetch, so the ~155 KB list is never inlined into the page.
	const chapters = (await listScripturePages().catch(() => []))
		.filter((p) => p.verse === null)
		.sort((a, b) => a.book_order - b.book_order || a.chapter - b.chapter);
	const i = chapters.findIndex((p) => p.book === params.book && p.chapter === chapter);
	return {
		page,
		prev: i > 0 ? nav(chapters[i - 1]) : null,
		next: i >= 0 && i < chapters.length - 1 ? nav(chapters[i + 1]) : null
	};
};
