import { getPlan, listPlans } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { EntryGenerator, PageLoad } from './$types';

// Prerender one page per plan — the slug list comes from the API at build
// time. The plans endpoint may lag on a fresh deploy (api + web build
// together), so degrade to no plan pages rather than fail the whole build;
// a later rebuild picks them up once the API is serving them.
export const entries: EntryGenerator = async () => {
	try {
		const plans = await listPlans('en');
		return plans.map((p) => ({ slug: p.slug }));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params, depends }) => {
	depends('app:lang');
	return { plan: await getPlan(params.slug, getLang()) };
};
