import { error } from '@sveltejs/kit';
import { getChapterWithLang, listBooks, MODERN_EDITION } from '$lib/library-public';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

// The Modern English edition at its own address. It used to exist only as
// `/books/<slug>/<n>?edition=modern`, whose canonical pointed at the original —
// so the one text on the site no other library carries could never be indexed,
// and the query param meant the build never baked it at all. Here it prerenders
// like any chapter, canonicalizes to itself, and is listed in the sitemap.
// `?edition=modern` still works: the chapter page forwards it here.
export const prerender = true;
export const trailingSlash = 'always';

// One entry per Modern English chapter, from the edition's own rows — its
// chapter count is its own, not assumed from the original's.
export const entries: EntryGenerator = async () => {
	const books = await listBooks(MODERN_EDITION);
	return books.flatMap((b) =>
		Array.from({ length: b.chapter_count }, (_, i) => ({
			slug: b.slug,
			order: String(i + 1)
		}))
	);
};

export const load: PageLoad = async ({ params, fetch }) => {
	const { data: chapter, language } = await orNotFound(() =>
		getChapterWithLang(params.slug, Number(params.order), MODERN_EDITION, fetch)
	);
	// The chapter fetch falls back to English on a 404, which here would put the
	// original text at the modern edition's address — a duplicate under a Modern
	// label. A work with no Modern English chapter has no page here.
	if (language !== MODERN_EDITION) error(404, 'Not found');
	return { chapter, slug: params.slug, language, edition: 'modern' as const };
};
