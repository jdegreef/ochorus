import { listAuthors } from '$lib/library-public';
import { ERAS, eraOf } from '$lib/eras';
import type { PageLoad } from './$types';

/**
 * Data for the crawl anchor (see +page.svelte). Deliberately the FULL author
 * list, not a page of it: this route exists so the prerenderer can reach every
 * localized `/authors/<slug>/` and `/biographies/era/<id>/`, and a partial list
 * would silently reinstate the gap it was added to close.
 *
 * `listAuthors` without a locale argument: the anchor only needs slugs and
 * birth years, both language-independent, and asking per-locale would make this
 * page's completeness depend on which bios happen to be translated.
 */
export const load: PageLoad = async () => {
	const authors = await listAuthors();
	// Only eras that actually contain a writer, matching the era route's own
	// `entries()` — prerendering an empty era would bake a page the sitemap
	// never advertises.
	const present = new Set(authors.map((a) => eraOf(a.birth_year)));
	return {
		slugs: authors.map((a) => a.slug),
		eras: ERAS.filter((e) => present.has(e.id)).map((e) => e.id)
	};
};
