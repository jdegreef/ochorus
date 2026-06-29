import { listBooks } from '$lib/library';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	const books = await listBooks();
	return { books };
};
