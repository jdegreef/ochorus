/**
 * `noindex` for the SPA fallback shell, baked in at build time.
 *
 * The static host answers every path with no prerendered file with `200.html`
 * (render.yaml's `/* -> /200.html` catch-all): typo'd slugs, dead WordPress
 * URLs, out-of-range chapters, the no-slash twin of every detail page. Every
 * page meant to be indexed is PRERENDERED to its own file and never loads this
 * shell, so nothing the shell serves is a page we want in the index — yet it
 * answered 200 with no robots directive in the HTML, and the only `noindex` was
 * the one `+error.svelte` adds after JavaScript runs. Google counts those as
 * soft 404s and keeps spending crawl budget re-rendering them.
 *
 * Baked into the raw HTML the crawler reads first, the directive is decided
 * before any rendering. The one cost: a page that SHOULD exist but missed the
 * build (the API lagging a release) is noindex until the next build prerenders
 * it — which `check-content-prerendered.mjs` exists to catch.
 *
 * SvelteKit renders the fallback at the synthetic path `/[fallback]`.
 */
export const FALLBACK_PATH = '/[fallback]';

export const FALLBACK_ROBOTS = '<meta name="robots" content="noindex" />';

export function markFallbackNoindex(html: string, pathname: string): string {
	if (pathname !== FALLBACK_PATH) return html;
	return html.replace('</head>', `\t${FALLBACK_ROBOTS}\n\t</head>`);
}
