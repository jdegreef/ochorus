/**
 * `sitemap.xml` — now a `<sitemapindex>` over per-type children.
 *
 * The assembly all lives in `$lib/sitemap`; this route only decides which
 * children exist and links them. See that module for why the split happened
 * (per-sitemap coverage reporting in Search Console — NOT the 50,000-URL
 * limit, which this site is two orders of magnitude away from).
 *
 * CHILDREN SIT AT THE ROOT — `/sitemap-chapters-en.xml`, not
 * `/sitemaps/chapters-en.xml`. The protocol scopes a sitemap to its own
 * directory: one under `/sitemaps/` may formally only claim URLs beneath
 * `/sitemaps/`. Google waives that for sitemaps reached through robots.txt or
 * Search Console, but Bing and crawl auditors (Screaming Frog) can read it
 * strictly, and a root-level name costs nothing to sidestep the question.
 *
 * `robots.txt` still names this one file. Crawlers discover the children
 * through the index, so nothing there needs to know the sections exist.
 */
import {
	sectionEntries,
	sections,
	sectionUrl,
	sitemapData
} from '$lib/sitemap';

export const prerender = true;

export async function GET() {
	const data = await sitemapData();
	// An EMPTY section is left out rather than linked. A child `<urlset>` with
	// no `<url>` in it is a promise of nothing, and Search Console reports it as
	// an error rather than an empty shelf. The child file is still built (its
	// route enumerates every section, and an unreached prerenderable route
	// fails the build) — it is simply unreferenced, which is the honest state.
	//
	// (`golive.verify_deployed` no longer reads this index for a per-locale
	// child NAME — chapters, which used to supply one, are no longer advertised.
	// It fetches the pages child and reads the locale out of its URLs instead.
	// See that function.)
	const live = sections().filter((s) => (sectionEntries(data, s)?.length ?? 0) > 0);

	const xml =
		'<?xml version="1.0" encoding="UTF-8"?>\n' +
		'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
		live.map((s) => `  <sitemap>\n    <loc>${sectionUrl(s)}</loc>\n  </sitemap>`).join('\n') +
		'\n</sitemapindex>\n';

	return new Response(xml, { headers: { 'content-type': 'application/xml' } });
}
