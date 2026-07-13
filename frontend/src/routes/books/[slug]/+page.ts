import { getBook, listBooks } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

// Canonical URL carries a trailing slash so this page prerenders to
// books/<slug>/index.html — the static host (Render) serves a directory index
// only for the trailing-slash URL, so this is what keeps real book pages served
// as prerendered HTML while a missing slug falls through to the not-found page.
export const trailingSlash = 'always';

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

// Refresh prerender: Finney + Brainerd (books, author bios, portrait) added
// via fixture; the web build prerendered before the API seeded them. 2026-07-13.
