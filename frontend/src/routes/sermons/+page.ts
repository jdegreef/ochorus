import { listSermons } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

/**
 * Prerender refresh 2026-07-17 (queue job #180): force an ochorus-web rebuild
 * after the api went live with the Luganda sermon Enteekateeka n'Ensonga mu
 * Kusaba (PR #186), so the /lg/sermons pages re-crawl and bake the new title.
 *
 * Prerender refresh 2026-07-17 (queue job #181): same again after the Luganda
 * sermon Ekisumuluzo ekya Zaabu eky'Okusaba (PR #188) went live.
 *
 * Prerender refresh 2026-07-18 (queue job #182): same again after the Luganda
 * sermon Ebisoboka by'Okukkiriza (PR #191) went live.
 */
export const load: PageLoad = async () => {
	// Tolerate a lagging/absent sermon endpoint at prerender time (see the
	// [slug] entries generator) — render an empty list rather than fail the build.
	try {
		return { sermons: await listSermons(getLang()) };
	} catch {
		return { sermons: [] };
	}
};
