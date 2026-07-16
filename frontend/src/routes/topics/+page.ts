import { listTopics } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

// Prerender refresh 2026-07-16: re-bake /topics and /topics/<slug> after the
// api went live with the topic scripture epigraphs + sermon memberships, so the
// prerendered pages pick up the accent/verse/"N books · M sermons" and the
// Sermons section (a same-deploy web build can prerender before seed_topics).
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
