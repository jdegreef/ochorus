import { listBooks } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ depends }) => {
	depends('app:lang');
	const books = await listBooks(getLang());
	return { books };
};
