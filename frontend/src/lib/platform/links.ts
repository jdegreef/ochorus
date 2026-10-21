/**
 * Where a tapped link goes in the app — pure, so it is tested without a
 * phone. The app serves the reader from its own origin (`capacitor://localhost`
 * on iOS, `https://localhost` on Android) and holds only the SPA: no feed, no
 * sitemaps, no prerendered files. So a link either stays in the app (the
 * router's), or leaves it for the system browser:
 *
 *   * another origin (Wikipedia, the API's EPUB, a share target) → the browser;
 *   * a file the WEBSITE serves (feed.xml, sitemap.xml, robots.txt, a PDF, any
 *     `download` link) → the same path on ochorus.com, in the browser — the
 *     app's copy is missing, or is a file its web view cannot show or save;
 *   * an absolute link to ochorus.com's own pages → that page, in the app.
 *
 * Anything else (mailto:, tel:) is left to the web view, which hands non-web
 * schemes to the system already.
 */

export type LinkTarget = { kind: 'external'; url: string } | { kind: 'internal'; path: string } | null;

/** scheme + host. Not `URL.origin`: that is the string "null" for a custom
 *  scheme like iOS's `capacitor://`, so every app link would look foreign. */
const originOf = (u: URL) => `${u.protocol}//${u.host}`;

/** A path that names a FILE rather than a reader page: its last segment has an
 *  extension (`/feed.xml`, `/sitemap-books.xml`, `/pdfs/humility.pdf`). The
 *  reader's own routes never end in one (they end in a slug or `/`). */
export function isFilePath(pathname: string): boolean {
	const last = pathname.split('/').pop() ?? '';
	return /\.[a-z0-9]{1,8}$/i.test(last) && !/\.html?$/i.test(last);
}

/**
 * @param href the link's href, as written
 * @param here the page it was tapped on (`location.href`)
 * @param siteUrl the website (`SITE_URL`, e.g. https://ochorus.com)
 * @param download whether the link carries a `download` attribute
 */
export function linkTarget(href: string, here: string, siteUrl: string, download = false): LinkTarget {
	let url: URL;
	let site: URL;
	try {
		url = new URL(href, here);
		site = new URL(siteUrl);
	} catch {
		return null;
	}
	const rest = `${url.pathname}${url.search}${url.hash}`;
	const fileish = download || isFilePath(url.pathname);
	if (originOf(url) === originOf(new URL(here))) {
		return fileish ? { kind: 'external', url: `${originOf(site)}${rest}` } : null;
	}
	if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
	if (originOf(url) === originOf(site) && !fileish) return { kind: 'internal', path: rest };
	return { kind: 'external', url: url.href };
}
