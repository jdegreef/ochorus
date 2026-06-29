import { getChapter } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, depends }) => {
	depends('app:lang');
	const chapter = await getChapter(params.slug, Number(params.order), getLang());
	return { chapter, slug: params.slug };
};
