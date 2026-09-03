import { getArticle, listArticles } from '$lib/library-public';
import { getLang } from '$lib/lang.svelte';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

// Trailing-slash canonical -> prerenders to articles/<slug>/index.html, which
// the static host serves as a directory index (see books/[slug] for the note).
export const trailingSlash = 'always';

// One page per article — the slug list comes from the API at build time. The
// endpoint may lag on a fresh deploy (api + web build together), so degrade to
// no article pages rather than fail the whole build; a later rebuild picks
// them up once the API is serving them.
export const entries: EntryGenerator = async () => {
	try {
		const articles = await listArticles('en');
		return articles.map((a) => ({ slug: a.slug }));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params }) => {
	const article = await orNotFound(() => getArticle(params.slug, getLang()));
	return { article };
};
