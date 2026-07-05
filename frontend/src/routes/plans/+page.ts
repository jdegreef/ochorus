import { listPlans } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ depends }) => {
	depends('app:lang');
	// Tolerate a lagging/absent plans endpoint at prerender time (api + web can
	// build together on a deploy) — render an empty list rather than fail the
	// build; a later rebuild picks the plans up.
	try {
		return { plans: await listPlans(getLang()) };
	} catch {
		return { plans: [] };
	}
};
