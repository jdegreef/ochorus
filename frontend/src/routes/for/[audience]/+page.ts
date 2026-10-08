import { error } from '@sveltejs/kit';
import { FOR_PAGES, forPage, pickBooks } from '$lib/forPages';
import { listBooks, type CoverBook } from '$lib/library-public';
import type { EntryGenerator, PageLoad } from './$types';

// The "Ochorus for …" pages ($lib/forPages): English-only, one per group.
// Prerenders to /for/<audience>/index.html, so links carry the slash
// (isSlashedPath).
export const prerender = true;
export const trailingSlash = 'always';

export const entries: EntryGenerator = () => FOR_PAGES.map((p) => ({ audience: p.slug }));

export const load: PageLoad = async ({ params, fetch }) => {
	const page = forPage(params.audience);
	if (!page) error(404, 'Not found');
	// The book shelf is decoration: a failed list leaves the page without it
	// rather than failing the page (the page's message stands on its own).
	let books: CoverBook[] = [];
	try {
		books = pickBooks(await listBooks('en', fetch), page.picks);
	} catch {
		books = [];
	}
	return { page, books };
};
