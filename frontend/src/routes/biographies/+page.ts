import { listAuthors, listBooks, type BookSummary } from '$lib/library-public';
import { loadShelf } from '$lib/loadShelf';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

// This page is prerendered per locale, baking whatever bios the API returns for
// getLang() at build time. So author-bio *content* translations must be live on
// the API before the web build runs — otherwise the localized page bakes English
// and needs a fresh ochorus-web deploy once the API catches up.
//
// Prerender refresh 2026-07-22: force an ochorus-web rebuild after the API went
// live with a complete set of localized mini-bios — every non-imprint author now
// has a short bio translated into es/lg/sw, so the /es|/lg|/sw biographies pages
// re-crawl and bake the translated blurbs instead of the English fallback.
//
// Prerender refresh 2026-09-07: migration 0127 gives 13 authors a portrait, and
// this shelf bakes each card's photo_url (and its schema.org image). Force a
// rebuild AFTER the API migration lands so the cards show the new portraits
// instead of the initials avatar.
export const load: PageLoad = async ({ fetch }) => {
	const lang = getLang();
	// The authors are the shelf: a failed fetch is REPORTED so the page can
	// offer Try again, rather than crashing to the 500 route (it was unguarded).
	const { items: authors, loadError } = await loadShelf(listAuthors(lang, fetch));
	// Books power the per-writer cover strip; degrade to no strips if unavailable
	// so the biographies still render.
	let books: BookSummary[] = [];
	try {
		books = await listBooks(lang, fetch);
	} catch {
		books = [];
	}
	return { authors, books, loadError };
};

// Biographies book counts are locale-aware (server-side) and prerendered per
// locale; a backend-only change to the count needs a web rebuild to refresh
// the static pages.
