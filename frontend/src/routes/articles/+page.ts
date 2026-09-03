import { listArticles } from '$lib/library-public';
import type { PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// English-only for now — articles are original site writing, not yet
// translated. The list comes from the same endpoint the [slug] entry generator
// and the sitemap read, so all three advertise exactly the same set. A lagging
// API degrades to an empty index rather than failing the build.
export const load: PageLoad = async () => ({
	articles: await listArticles('en').catch(() => [])
});
