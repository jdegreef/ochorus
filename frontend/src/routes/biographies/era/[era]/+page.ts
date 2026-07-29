import { listAuthors, listBooks, type BookSummary } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import { error } from '@sveltejs/kit';
import { ERAS, eraById, eraOf } from '$lib/eras';
import type { EntryGenerator, PageLoad } from './$types';

// Trailing-slash canonical -> prerenders to era/<id>/index.html, served as a
// directory index by the static host (see authors/[slug] for the full note).
export const trailingSlash = 'always';

// One prerendered page per church-history era that actually has writers — an
// empty era (e.g. no pre-1480 authors) is skipped rather than baking a bare
// page. Authors render in every locale via the bio fallback, so the 'en' set
// is the same set every locale would show; presence is locale-independent.
export const entries: EntryGenerator = async () => {
	const authors = await listAuthors('en');
	const present = new Set(authors.map((a) => eraOf(a.birth_year)));
	return ERAS.filter((e) => present.has(e.id)).map((e) => ({ era: e.id }));
};

// Prerendered per locale, baking whatever bios the API returns for getLang() at
// build time — same content-race as the biographies index: a bio translation
// must be live on the API before the web build to bake the localized text.
export const load: PageLoad = async ({ params }) => {
	const era = eraById(params.era);
	if (!era) throw error(404, 'Unknown era');
	const lang = getLang();
	const authors = await listAuthors(lang);
	// Books power the per-writer cover strips; degrade to none if unavailable so
	// the page still renders.
	let books: BookSummary[] = [];
	try {
		books = await listBooks(lang);
	} catch {
		books = [];
	}
	return { eraId: era.id, authors, books };
};
