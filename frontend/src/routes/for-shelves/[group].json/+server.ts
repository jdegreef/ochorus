/**
 * An "Ochorus for …" page's starter shelf, as a static JSON file written at
 * build time ($lib/forPages). The page reads this rather than the live book
 * list: the list is ~220 books, and SvelteKit inlines a load's fetched
 * response into the prerendered HTML, so the page would carry every book to
 * draw six covers — and a client-side visit would download the list again.
 */
import { error, json } from '@sveltejs/kit';
import { FOR_PAGES, forPage, forShelf } from '$lib/forPages';
import { listBooks } from '$lib/library-public';
import type { EntryGenerator } from './$types';

export const prerender = true;

export const entries: EntryGenerator = () => FOR_PAGES.map((p) => ({ group: p.slug }));

export async function GET({ params, fetch }) {
	const page = forPage(params.group);
	if (!page) error(404, `No page for '${params.group}'.`);
	const shelf = forShelf(await listBooks('en', fetch), page.picks);
	// None of the picks is published: fail the build rather than ship the page
	// with no books (the picks need replacing in $lib/forPages).
	if (!shelf.length) error(500, `No published book among the '${page.slug}' picks.`);
	return json(shelf);
}
