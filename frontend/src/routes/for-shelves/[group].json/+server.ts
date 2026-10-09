/**
 * An "Ochorus for …" page's live sections — its starter shelves, its plans,
 * the printable leader's guides and its offline pack — as one static JSON file
 * written at build time ($lib/forPages). The page reads this rather than the
 * live lists: the book list is ~220 books, and SvelteKit inlines a load's
 * fetched response into the prerendered HTML, so the page would carry every
 * book to draw a few rows of covers — and a client-side visit would download
 * the list again.
 */
import { error, json } from '@sveltejs/kit';
import {
	FOR_PAGES,
	forPage,
	forPlans,
	forShelf,
	toOfflineBook,
	type ForPage,
	type ForShelfData
} from '$lib/forPages';
import { getAudienceShelf, getBook, listBooks, listPlans, toCoverBook } from '$lib/library-public';
import type { EntryGenerator } from './$types';

export const prerender = true;

export const entries: EntryGenerator = () => FOR_PAGES.map((p) => ({ group: p.slug }));

type Fetch = typeof globalThis.fetch;

/** The books with a printable leader's guide, children's hub first, each once. */
async function guideBooks(fetch: Fetch) {
	const hubs = await Promise.all([getAudienceShelf('young_readers', 'en', fetch), getAudienceShelf('teens', 'en', fetch)]);
	const seen = new Set<string>();
	return hubs
		.flatMap((h) => h.leader_guides ?? [])
		.filter((b) => !seen.has(b.slug) && seen.add(b.slug))
		.map(toCoverBook);
}

/** The pack's picks that are published and have a file to download, in order.
 *  Only published slugs are asked for, so an unpublished pick costs no 404. */
async function offlinePack(page: ForPage, published: Set<string>, fetch: Fetch) {
	const slugs = (page.offline?.picks ?? []).filter((s) => published.has(s));
	const details = await Promise.all(slugs.map((s) => getBook(s, 'en', fetch)));
	return details.flatMap((d) => toOfflineBook(d) ?? []);
}

export async function GET({ params, fetch }) {
	const page = forPage(params.group);
	if (!page) error(404, `No page for '${params.group}'.`);
	const english = await listBooks('en', fetch);
	const published = new Set(english.map((b) => b.slug));
	const [plans, guides, offline] = await Promise.all([
		listPlans('en', fetch).then((all) => forPlans(all, page.plans)),
		page.guides ? guideBooks(fetch) : [],
		page.offline ? offlinePack(page, published, fetch) : []
	]);
	const data: ForShelfData = {
		shelves: page.shelves.map((s) => ({ title: s.title, note: s.note, books: forShelf(english, s.picks) })),
		plans,
		guides,
		offline
	};
	// A shelf with none of its picks published, or a section the page's own
	// buttons point at coming back empty: fail the build rather than ship a
	// bare heading or a dead link (the picks need replacing in $lib/forPages).
	const empty = data.shelves.find((s) => !s.books.length);
	if (empty) error(500, `No published book on the '${page.slug}' shelf '${empty.title}'.`);
	const sections: Record<string, unknown[]> = {
		'#shelves': data.shelves,
		'#plans': plans,
		'#guides': guides,
		'#offline': offline
	};
	for (const { href } of [page.primary, page.secondary]) {
		if (href in sections && !sections[href].length) error(500, `'${page.slug}' links ${href}, which is empty.`);
	}
	return json(data);
}
