import { error } from '@sveltejs/kit';
import { getLang } from '$lib/lang.svelte';
import { listBooks } from '$lib/library-public';
import { eraBooks, erasWithBooks } from '$lib/bookHubs';
import { eraById } from '$lib/eras';
import type { EntryGenerator, PageLoad } from './$types';

// Trailing-slash canonical -> prerenders to era/<era>/index.html, served as a
// directory index by the static host (see books/[slug] for the full note).
export const trailingSlash = 'always';

// Every era with enough English books ($lib/bookHubs); other locales are
// reached by the crawl through links that check the same floor.
export const entries: EntryGenerator = async () => {
	try {
		return erasWithBooks(await listBooks('en')).map((era) => ({ era }));
	} catch {
		return [];
	}
};

// Global fetch, as the tradition route: only what the page draws is returned.
export const load: PageLoad = async ({ params }) => {
	const era = eraById(params.era);
	if (!era) throw error(404, 'Not found');
	const books = await listBooks(getLang());
	const eras = erasWithBooks(books);
	if (!eras.includes(era.id)) throw error(404, 'Not found');
	return { era, books: eraBooks(era.id, books), others: eras.filter((e) => e !== era.id) };
};
