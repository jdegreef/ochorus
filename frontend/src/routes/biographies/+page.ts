import { listAuthors } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	const authors = await listAuthors(getLang());
	return { authors };
};
