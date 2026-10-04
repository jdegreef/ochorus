import { error, redirect } from '@sveltejs/kit';
import { building } from '$app/environment';
import { ApiError } from '$lib/api';
import { getChapterExact, listBooks, MODERN_EDITION } from '$lib/library-public';
import { localizeHref } from '$lib/href';
import { bookChapterPath } from '$lib/reading-schema';
import { chapterEntries } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

// The Modern English edition at its own address. It used to exist only as
// `/books/<slug>/<n>?edition=modern`, whose canonical pointed at the original —
// so the one text no other library carries could never be indexed, and the
// query param meant the build never baked it at all. Here it prerenders like
// any chapter, canonicalizes to itself, and is listed in the sitemap once
// reviewed. `?edition=modern` still works: the original route redirects here.
export const prerender = true;
export const trailingSlash = 'always';

// One entry per Modern English chapter, from the edition's own rows — its
// chapter count is its own, not assumed from the original's.
export const entries: EntryGenerator = async () => chapterEntries(await listBooks(MODERN_EDITION));

export const load: PageLoad = async ({ params, url, fetch }) => {
	const order = Number(params.order);
	try {
		const chapter = await getChapterExact(params.slug, order, MODERN_EDITION, fetch);
		return { chapter, slug: params.slug, language: MODERN_EDITION, edition: 'modern' as const };
	} catch (e) {
		if (!(e instanceof ApiError && e.status === 404)) throw e;
		// No Modern English chapter here. At build time that is a page that does
		// not exist; at runtime it is usually an old `?edition=modern` link to a
		// work that has no modern edition — read the original instead.
		if (building) error(404, 'Not found');
		redirect(307, localizeHref(`${bookChapterPath(params.slug, order, false)}${url.search}`));
	}
};
