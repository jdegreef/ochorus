/**
 * The child sitemaps — one route serving every section.
 *
 * One dynamic route rather than nine files: the sections are one list
 * (`$lib/sitemap`), and splitting them across routes would mean a new
 * directory every time a locale goes live. This way a launch adds its
 * `chapters-<code>` child on the next build with no hand-edit, exactly as the
 * flat sitemap gained a locale's URLs before the split.
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
