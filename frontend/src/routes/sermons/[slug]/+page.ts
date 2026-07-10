import { getSermon, listSermons } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

// Prerender one page per sermon — the slug list comes from the API at build
// time. The sermon endpoint may lag on a fresh deploy (api + web build together),
// so degrade to no sermon pages rather than fail the whole build; a later
// rebuild picks them up once the API is serving them.
export const entries: EntryGenerator = async () => {
	try {
		const sermons = await listSermons('en');
		return sermons.map((s) => ({ slug: s.slug }));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params }) => {
	const sermon = await orNotFound(() => getSermon(params.slug, getLang()));
	return { sermon };
};
