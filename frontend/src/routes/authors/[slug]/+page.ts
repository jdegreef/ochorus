import { getAuthor, listAuthors, listBooks } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { EntryGenerator, PageLoad } from './$types';

// Prerender a page for every author who has books or a biography. The slug set
// is the union of book authors and bio'd authors, from the API at build time.
export const entries: EntryGenerator = async () => {
	const [books, authors] = await Promise.all([listBooks('en'), listAuthors()]);
	const slugs = new Set<string>();
	for (const b of books) slugs.add(b.author.slug);
	for (const a of authors) slugs.add(a.slug);
	return [...slugs].map((slug) => ({ slug }));
};

export const load: PageLoad = async ({ params, depends }) => {
	depends('app:lang');
	const author = await getAuthor(params.slug, getLang());
	return { author };
};
