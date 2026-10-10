/**
 * An "Ochorus for …" page's live sections — its starter shelves, its plans,
 * the printable leader's guides, its offline pack, its writers, its quotation
 * and the library's numbers — as one static JSON file
 * written at build time ($lib/forPages). The page reads this rather than the
 * live lists: the book list is ~220 books, and SvelteKit inlines a load's
 * fetched response into the prerendered HTML, so the page would carry every
 * book to draw a few rows of covers — and a client-side visit would download
 * the list again.
 */
import { error, json } from '@sveltejs/kit';
import { FOR_PAGES, forPage } from '$lib/forPages';
import { forShelfData } from '$lib/forShelfData';
import type { EntryGenerator } from './$types';

export const prerender = true;

export const entries: EntryGenerator = () => FOR_PAGES.map((p) => ({ group: p.slug }));

export async function GET({ params, fetch }) {
	const page = forPage(params.group);
	if (!page) error(404, `No page for '${params.group}'.`);
	const data = await forShelfData(page, fetch);
	// A shelf with none of its picks published: fail the build rather than ship
	// a bare heading (the picks need replacing in $lib/forPages). An empty plan,
	// guide or offline section is not an error — the page drops it, and a
	// button that pointed there goes to its fallback page instead (forHref).
	// CI's API, seeded from the fixture alone, has only a few plans.
	const empty = data.shelves.find((s) => !s.books.length);
	if (empty) error(500, `No published book on the '${page.slug}' shelf '${empty.title}'.`);
	return json(data);
}
