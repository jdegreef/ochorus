import { getChapter } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

// The reader is per-user and dynamic (one page per chapter) — keep it an SPA.
export const prerender = false;
export const ssr = false;

export const load: PageLoad = async ({ params }) => {
	const chapter = await getChapter(params.slug, Number(params.order), getLang());
	return { chapter, slug: params.slug };
};
