/**
 * The child sitemaps — one route serving every section.
 *
 * One dynamic route rather than a file per section: the sections are one list
 * (`$lib/sitemap`), and splitting them across routes would mean a new directory
 * every time the set changes. This way whatever `sections()` returns is served
 * with no hand-edit — and were the per-locale `chapters-<code>` children ever
 * restored (see `sections()`), a launch would add its child on the next build
 * with no new route, exactly as the flat sitemap gained a locale's URLs before
 * the split.
 */
import { error } from '@sveltejs/kit';
import type { EntryGenerator } from './$types';
import {
	sectionEntries,
	sectionLocale,
	sections,
	sitemapData,
	urlsetXml
} from '$lib/sitemap';

export const prerender = true;

export const entries: EntryGenerator = async () =>
	sections().map((section) => ({ section }));

export async function GET({ params }) {
	const data = await sitemapData();
	const entries = sectionEntries(data, params.section);
	// Unknown section — a stale link, or a locale that has since been pulled.
	// 404 rather than an empty `<urlset>`: prerendering never asks for one (the
	// generator above enumerates the real list), so reaching here at all means
	// the URL was invented, and a 200 would let it be indexed as a valid-but-
	// empty sitemap.
	if (!entries) error(404, `No sitemap section '${params.section}'.`);
	return new Response(urlsetXml(entries, sectionLocale(params.section)), {
		headers: { 'content-type': 'application/xml' }
	});
}
