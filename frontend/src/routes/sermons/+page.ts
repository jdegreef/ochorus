import { listSermons } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ depends }) => {
	depends('app:lang');
	// Tolerate a lagging/absent sermon endpoint at prerender time (see the
	// [slug] entries generator) — render an empty list rather than fail the build.
	try {
		return { sermons: await listSermons(getLang()) };
	} catch {
		return { sermons: [] };
	}
};
