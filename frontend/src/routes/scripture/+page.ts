import { listScripturePages } from '$lib/library-public';
import type { PageLoad } from './$types';

// The hub for the scripture graph, and the reason its pages are not orphans: a
// page reachable only from the sitemap tells search engines you do not value it
// either. From here every chapter page is one click, every verse page two.
export const prerender = true;
export const trailingSlash = 'always';

export const load: PageLoad = async () => {
	// Degrade to an empty index rather than failing the build: the API can lag a
	// simultaneous deploy, and a later rebuild picks the pages up. Consistent
	// with how /topics and /plans treat the same race.
	try {
		return { pages: await listScripturePages() };
	} catch {
		return { pages: [] };
	}
};
