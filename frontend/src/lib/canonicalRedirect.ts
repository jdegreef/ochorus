import { locales } from '$lib/paraglide/runtime';

/**
 * The production static service's own Render hostname. It serves the whole
 * site alongside the real domain, so every page exists twice. Named exactly,
 * not as "*.onrender.com": preview environments get their own onrender hosts
 * and must keep working where they are.
 */
export const RENDER_HOST = 'ochorus-web.onrender.com';

/** Index pages whose route exports `trailingSlash = 'always'`. */
const SLASHED_INDEXES = new Set(['articles', 'authors', 'originals', 'quotes', 'scripture', 'series']);
/** Sections whose every deeper page exports `trailingSlash = 'always'`. */
const SLASHED_SECTIONS = new Set([
	'articles',
	'authors',
	'books',
	'plans',
	'quotes',
	'scripture',
	'series',
	'sermons',
	'topics'
]);

/**
 * Whether a path (locale prefix and all) belongs to a route that prerenders to
 * `<path>/index.html` — i.e. exports `trailingSlash = 'always'`. Kept to that
 * rule, not to `$lib/href`'s narrower link-builder list: any such route's
 * no-slash URL is a shell duplicate. `canonicalRedirect.test.ts` walks the
 * route tree so a new slashed route can't be missed.
 */
export function isSlashedPath(path: string): boolean {
	const segments = path.split('/').filter(Boolean);
	const body = locales.includes(segments[0] as (typeof locales)[number])
		? segments.slice(1)
		: segments;
	if (!body.length) return false;
	// A real file extension is an asset, not a page.
	if (/\.[a-z0-9]{2,5}$/i.test(body[body.length - 1])) return false;
	if (body.length === 1) return SLASHED_INDEXES.has(body[0]);
	if (body[0] === 'biographies') return body[1] === 'era' && body.length === 3;
	return SLASHED_SECTIONS.has(body[0]);
}

/**
 * Where a page loaded at `loc` should really be, or null if it is already there.
 *
 * Two duplicates the static host cannot 301 (render.yaml explains why the
 * no-slash rule would loop, and it cannot tell hosts apart):
 *
 *   * `/books/<slug>` — the no-slash twin of a prerendered page. It matches no
 *     file and gets the 200.html shell, which is `noindex`
 *     ($lib/fallbackShell). Links and old index entries still point at it.
 *   * `ochorus-web.onrender.com/...` — the production service's default host.
 *
 * Google treats a JavaScript `location.replace` as a redirect and consolidates
 * the signals onto the target, which a `noindex` alone does not do: the equity
 * of a link to the duplicate would otherwise be dropped with it. Run before
 * hydration (hooks.client `init`), so a reader only ever sees the real page.
 */
export function canonicalRedirect(
	loc: { hostname: string; pathname: string; search: string; hash: string },
	siteUrl: string
): string | null {
	// Collapse leading slashes: "//books/x" as a target would be read as the
	// protocol-relative URL of a host called "books".
	const pathname = `/${loc.pathname.replace(/^\/+/, '')}`;
	const slashed = isSlashedPath(pathname) && !pathname.endsWith('/') ? `${pathname}/` : pathname;
	const target = slashed + loc.search + loc.hash;
	const site = new URL(siteUrl);
	if (loc.hostname === RENDER_HOST && site.hostname !== RENDER_HOST) return site.origin + target;
	return slashed !== loc.pathname ? target : null;
}
