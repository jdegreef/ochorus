import { SITE_URL } from '$lib/config';
import { listAuthors, listBooks } from '$lib/library';

export const prerender = true;

export async function GET() {
	const [books, authors] = await Promise.all([listBooks('en'), listAuthors()]);

	const authorSlugs = new Set<string>();
	for (const b of books) authorSlugs.add(b.author.slug);
	for (const a of authors) authorSlugs.add(a.slug);

	const paths = [
		'/',
		'/books',
		'/biographies',
		'/about',
		'/contact',
		...books.map((b) => `/books/${b.slug}`),
		...[...authorSlugs].map((s) => `/authors/${s}`)
	];

	const xml =
		'<?xml version="1.0" encoding="UTF-8"?>\n' +
		'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
		paths.map((p) => `  <url><loc>${SITE_URL}${p}</loc></url>`).join('\n') +
		'\n</urlset>\n';

	return new Response(xml, { headers: { 'content-type': 'application/xml' } });
}
