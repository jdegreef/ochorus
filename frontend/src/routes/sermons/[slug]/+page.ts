import { getSermon, listSermons } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { EntryGenerator, PageLoad } from './$types';

// Prerender one page per sermon — the slug list comes from the API at build time.
export const entries: EntryGenerator = async () => {
	const sermons = await listSermons('en');
	return sermons.map((s) => ({ slug: s.slug }));
};

export const load: PageLoad = async ({ params, depends }) => {
	depends('app:lang');
	const sermon = await getSermon(params.slug, getLang());
	return { sermon };
};
