import { listBooks } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ depends }) => {
	depends('app:lang');
	return { books: await listBooks(getLang()) };
};
