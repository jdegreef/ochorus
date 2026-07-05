import { getBook, listBooks } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { EntryGenerator, PageLoad } from './$types';

// Prerender one page per book — the slug list comes from the API at build time.
export const entries: EntryGenerator = async () => {
	const books = await listBooks('en');
	return books.map((b) => ({ slug: b.slug }));
};

export const load: PageLoad = async ({ params, depends }) => {
	depends('app:lang');
	const book = await getBook(params.slug, getLang());
	return { book };
};
