import { listBooks, listAuthors } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ depends }) => {
	depends('app:lang');
	const [books, authors] = await Promise.all([listBooks(getLang()), listAuthors()]);
	return {
		featured: books.slice(0, 6),
		totalBooks: books.length,
		authors: authors.filter((a) => a.book_count > 0)
	};
};
