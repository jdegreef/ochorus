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

// Prev/next among the CHAPTER pages, in canonical Bible order — so a reader (and
// a crawler) can walk the reverse index instead of returning to the hub each
// time. Neighbours are the adjacent QUALIFYING pages (not chapter ± 1, which may
// never have been built), read from the same list the entry generator uses.
type ScriptureNav = { href: string; label: string } | null;

export const load: PageLoad = async ({ params }) => {
	const chapter = Number(params.chapter);
	const [page, all] = await Promise.all([
		orNotFound(() => getScripturePage(params.book, chapter)),
		listScripturePages().catch(() => [])
	]);
	const chapters = all
		.filter((p) => p.verse === null)
		.sort((a, b) => a.book_order - b.book_order || a.chapter - b.chapter);
	const i = chapters.findIndex((p) => p.book === params.book && p.chapter === chapter);
	const nav = (p: (typeof chapters)[number] | undefined): ScriptureNav =>
		p ? { href: `/scripture/${p.book}/${p.chapter}/`, label: `${p.book_title} ${p.chapter}` } : null;
	return {
		page,
		prev: i > 0 ? nav(chapters[i - 1]) : null,
		next: i >= 0 && i < chapters.length - 1 ? nav(chapters[i + 1]) : null
	};
};
