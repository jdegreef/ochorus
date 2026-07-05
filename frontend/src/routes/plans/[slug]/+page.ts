import { getPlan } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, depends }) => {
	depends('app:lang');
	return { plan: await getPlan(params.slug, getLang()) };
};
