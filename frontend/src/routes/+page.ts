import { listBooks, listAuthors } from '$lib/library';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	const [books, authors] = await Promise.all([listBooks(), listAuthors()]);
	return {
		featured: books.slice(0, 6),
		totalBooks: books.length,
		authors: authors.filter((a) => a.book_count > 0)
	};
};
