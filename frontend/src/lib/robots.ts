import { locales } from '$lib/paraglide/runtime';

/**
 * Paths with nothing to index: account/admin shells, and internal search.
 * Never advertised in the sitemap (sitemap.ts filters its static pages by this
 * list) — a URL both advertised and disallowed is a Search Console error.
 */
export const APP_ONLY = [
	'/admin',
	'/settings',
	'/login',
	'/account',
	'/notebook',
	'/favorites',
	'/reset-password',
	'/search'
] as const;

/**
 * What robots.txt blocks for an app-only path. Search is the exception: its
 * results (`?q=…`, thin and endlessly parameterised) are blocked, but the bare
 * page stays crawlable so its `noindex` can be read — a disallowed URL linked
 * from every page's nav ends up "Indexed, though blocked by robots.txt".
 */
const blocked = (path: string) => (path === '/search' ? '/search?' : path);

/**
 * One `Disallow` per app-only path per UI locale. A Disallow is a path PREFIX,
 * so `/search` never covered `/es/search?q=…` — every locale's copy was open.
 */
export const appOnlyDisallows = (): string[] =>
	APP_ONLY.flatMap((p) =>
		locales.map((l) => `Disallow: ${l === 'en' ? '' : `/${l}`}${blocked(p)}`)
	);
