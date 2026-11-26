import { error } from '@sveltejs/kit';
import { getLang } from '$lib/lang.svelte';
import { listBooks, listHubs } from '$lib/library-public';
import { traditionBooks, traditionsWithBooks } from '$lib/bookHubs';
import type { EntryGenerator, PageLoad } from './$types';

// Trailing-slash canonical -> prerenders to tradition/<slug>/index.html, served
// as a directory index by the static host (see books/[slug] for the full note).
export const trailingSlash = 'always';

// Every English tradition with enough books ($lib/bookHubs). Another locale's
// pages are reached by the crawl, through links that check the same floor
// against that locale's books. An API lagging this deploy builds none.
export const entries: EntryGenerator = async () => {
	try {
		const [hubs, books] = await Promise.all([listHubs('en'), listBooks('en')]);
		return traditionsWithBooks(hubs, books).map((h) => ({ slug: h.slug }));
	} catch {
		return [];
	}
};

// Global fetch, not the load's: the prerender would inline the whole shelf into
// every page. Only what the page draws is returned.
export const load: PageLoad = async ({ params }) => {
	const lang = getLang();
	const [hubs, books] = await Promise.all([listHubs(lang), listBooks(lang)]);
	const traditions = traditionsWithBooks(hubs, books);
	const hub = traditions.find((h) => h.slug === params.slug);
	if (!hub) throw error(404, 'Not found');
	return {
		hub,
		books: traditionBooks(hub, books),
		others: traditions.filter((h) => h !== hub).map((h) => ({ slug: h.slug, label: h.label }))
	};
};
