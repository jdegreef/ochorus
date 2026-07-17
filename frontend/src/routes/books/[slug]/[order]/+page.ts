import { getChapter, MODERN_EDITION } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import { orNotFound } from '$lib/loadHelpers';
import type { PageLoad } from './$types';

// The reader is per-user and dynamic (one page per chapter) — keep it an SPA.
export const prerender = false;
export const ssr = false;

export const load: PageLoad = async ({ params, url }) => {
	// ?edition=modern reads the Modern English edition (en-modern) instead of the
	// locale copy. It's a per-book content mode carried in the URL — not the UI
	// locale — so it only applies to English works that have an edition.
	const modern = url.searchParams.get('edition') === 'modern';
	const chapter = await orNotFound(() =>
		getChapter(params.slug, Number(params.order), modern ? MODERN_EDITION : getLang())
	);
	return { chapter, slug: params.slug, edition: modern ? 'modern' : null };
};
