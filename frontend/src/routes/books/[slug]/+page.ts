import { getBook, listBooks } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

// Prerender one page per book — the slug list comes from the API at build time.
export const entries: EntryGenerator = async () => {
	const books = await listBooks('en');
	return books.map((b) => ({ slug: b.slug }));
};

export const load: PageLoad = async ({ params }) => {
	const book = await orNotFound(() => getBook(params.slug, getLang()));
	return { book };
};

// New public-domain books/sermons are prerendered per slug; a backend-only
// content merge skips the web build, so new /books/<slug> pages need this
// rebuild to exist as static HTML.

// Book detail is prerendered per locale; a backend-only content merge skips
// the web build, so a newly-translated book (e.g. the-inner-chamber in lg)
// needs this rebuild to prerender in that language.
