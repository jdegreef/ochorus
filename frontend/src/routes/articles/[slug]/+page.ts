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
	// getLang() (not a hardcoded 'en') is intentional: the detail page is already
	// built translation-ready — self-referential canonical + hreflang from
	// available_languages — while the index, entries() and sitemap stay English-
	// only for now. getArticle falls back to English on a 404, so a localized URL
	// degrades to the English original rather than 404ing. Don't "fix" this to
	// 'en' to match the others; it's the one place that must lead the rollout.
	const article = await orNotFound(() => getArticle(params.slug, getLang()));
	return { article };
};
