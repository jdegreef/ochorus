import { getChapter } from '$lib/library';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
	const chapter = await getChapter(params.slug, Number(params.order));
	return { chapter, slug: params.slug };
};
