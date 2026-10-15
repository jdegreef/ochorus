/**
 * An "Ochorus for …" page's live sections ($lib/forShelves) as one static JSON
 * file written at build time — the English page's; each other language the
 * pages are written in has its own beside it ([locale]/[group].json). The page
 * reads this rather than the live lists: the book list is ~220 books, and
 * SvelteKit inlines a load's fetched response into the prerendered HTML, so
 * the page would carry every book to draw a few rows of covers — and a
 * client-side visit would download the list again.
 */
import { error, json } from '@sveltejs/kit';
import { FOR_PAGES, forPage } from '$lib/forPages';
import { buildForShelf } from '$lib/forShelves';
import type { EntryGenerator } from './$types';

export const prerender = true;

export const entries: EntryGenerator = () => FOR_PAGES.map((p) => ({ group: p.slug }));

export async function GET({ params, fetch }) {
	const page = forPage(params.group);
	if (!page) error(404, `No page for '${params.group}'.`);
	return json(await buildForShelf(page, 'en', fetch));
}
