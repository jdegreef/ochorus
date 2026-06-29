import { listAuthors } from '$lib/library';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	const authors = await listAuthors();
	return { authors };
};
