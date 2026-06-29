import { getBook } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, depends }) => {
	depends('app:lang');
	const book = await getBook(params.slug, getLang());
	return { book };
};
