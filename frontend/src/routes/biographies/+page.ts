import { listAuthors, listBooks, type BookSummary } from '$lib/library';
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
export const load: PageLoad = async () => {
	const lang = getLang();
	const authors = await listAuthors(lang);
	// Books power the per-writer cover strip; degrade to no strips if unavailable
	// so the biographies still render.
	let books: BookSummary[] = [];
	try {
		books = await listBooks(lang);
	} catch {
		books = [];
	}
	return { authors, books };
};

// Biographies book counts are locale-aware (server-side) and prerendered per
// locale; a backend-only change to the count needs a web rebuild to refresh
// the static pages.
