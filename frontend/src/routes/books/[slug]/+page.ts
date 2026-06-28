import { getBook } from '$lib/library';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
	const book = await getBook(params.slug);
	return { book };
};
