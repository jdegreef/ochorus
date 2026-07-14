import { listTopics } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	// Tolerate a lagging/absent topics endpoint at prerender time (api + web can
	// build together on a deploy) — render an empty list rather than fail the
	// build; a later rebuild picks the topics up.
	try {
		return { topics: await listTopics(getLang()) };
	} catch {
		return { topics: [] };
	}
};
