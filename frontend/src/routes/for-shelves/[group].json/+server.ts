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
	FOR_ANCHORS,
	FOR_PAGES,
	isForAnchor,
	pageLinks,
	forPage,
	forPlans,
	forShelf,
	toOfflineBook,
	type ForPage,
	type ForShelfData
} from '$lib/forPages';
import { getAudienceShelf, getBook, guideBooks, listBooks, listPlans, toCoverBook } from '$lib/library-public';
import type { EntryGenerator } from './$types';

export const prerender = true;

export const entries: EntryGenerator = () => FOR_PAGES.map((p) => ({ group: p.slug }));

type Fetch = typeof globalThis.fetch;

/** The books with a printable leader's guide, children's hub first — the
 *  same two hubs, in the same order, as the guide route's prerender entries. */
async function leaderGuides(fetch: Fetch) {
	const hubs = await Promise.all([getAudienceShelf('young_readers', 'en', fetch), getAudienceShelf('teens', 'en', fetch)]);
	return guideBooks(hubs).map(toCoverBook);
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
	// All at once: only the offline pack waits, and only on the book list.
	const books = listBooks('en', fetch);
	const [english, plans, guides, offline] = await Promise.all([
		books,
		listPlans('en', fetch).then((all) => forPlans(all, page.plans)),
		page.guides ? leaderGuides(fetch) : [],
		page.offline ? books.then((all) => offlinePack(page, new Set(all.map((b) => b.slug)), fetch)) : []
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
	for (const href of pageLinks(page).filter(isForAnchor)) {
		if (!data[FOR_ANCHORS[href].section].length) error(500, `'${page.slug}' links ${href}, which is empty.`);
	}
	return json(data);
}
