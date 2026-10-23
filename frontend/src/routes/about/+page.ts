import { building } from '$app/environment';
import { readHomeSnapshot } from '$lib/homeSnapshot';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

// The library's totals for the stats band — the home page's own snapshot, so
// About and home can't disagree (About once said "100+ titles" and "90+
// sermons" beside home's 286 and 251). Loud while building, like home; at
// runtime a failed read just drops the two library figures.
export const load: PageLoad = async ({ fetch }) => {
	try {
		const { counts } = await readHomeSnapshot(fetch, getLang());
		return { counts };
	} catch (err) {
		if (building) throw err;
		return { counts: null };
	}
};
