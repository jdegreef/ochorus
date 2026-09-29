import { building } from '$app/environment';
import { listAuthors, listBooks } from '$lib/library-public';
import { getLang } from '$lib/lang.svelte';
import { ERAS, eraOf } from '$lib/eras';
import type { PageLoad } from './$types';

// Prerenders to authors/index.html, which the static host serves natively for
// /authors/ — no Render rewrite needed ($lib/href SLASHED_PAGES).
export const trailingSlash = 'always';

/**
 * The library A–Z ($lib/authorIndex). Two lists, fetched together:
 *
 *   * the WRITERS in English — every listed writer, whatever this locale has
 *     translated. Names and dates are language-independent, and a per-locale
 *     list would make the crawl anchor's completeness depend on which bios
 *     happen to be translated. (The page adds any writer the list omits but
 *     who has a book here — see authorIndex.)
 *   * the BOOKS in this locale — no English fallback, so each writer lists
 *     exactly the editions a reader of this language can open.
 *
 * A failure THROWS during the build, deliberately — the home page's `shelf()`
 * stance, not `loadShelf`'s. This page is the prerender's only seed for every
 * localized `/authors/<slug>/` and `/biographies/era/<id>/` page
 * (svelte.config.js); baked empty, all of those would ship as the noindex
 * shell while the sitemap still lists them. A loud build beats that. In the
 * browser a failure is reported (`loadError`), and Try again re-runs this.
 */
export const load: PageLoad = async ({ fetch }) => {
	const lang = getLang();
	try {
		const [authors, books] = await Promise.all([listAuthors('en', fetch), listBooks(lang, fetch)]);
		// Only eras that actually contain a writer, matching the era route's own
		// `entries()` — linking an empty era would bake a page the sitemap never
		// advertises.
		const present = new Set(authors.map((a) => eraOf(a.birth_year)));
		return { authors, books, eras: ERAS.filter((e) => present.has(e.id)), loadError: false };
	} catch (e) {
		if (building) throw e;
		return { authors: [], books: [], eras: [], loadError: true };
	}
};
