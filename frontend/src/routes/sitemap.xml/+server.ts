import { SITE_URL } from '$lib/config';
import { listAuthors, listBooks, listSermons } from '$lib/library';

export const prerender = true;

export async function GET() {
	const [books, authors, sermons] = await Promise.all([
		listBooks('en'),
		listAuthors(),
		// Tolerate a lagging/absent sermon endpoint at build time — omit sermon
		// URLs rather than fail the sitemap prerender.
		listSermons('en').catch(() => [])
	]);

	const authorSlugs = new Set<string>();
	for (const b of books) authorSlugs.add(b.author.slug);
	for (const a of authors) authorSlugs.add(a.slug);

	const paths = [
		'/',
		'/books',
		'/sermons',
		'/biographies',
		'/about',
		'/contact',
		// Detail pages canonicalize to a trailing slash (prerendered as directory
		// indexes; the static host serves those only for the trailing-slash URL).
		...books.map((b) => `/books/${b.slug}/`),
		...sermons.map((s) => `/sermons/${s.slug}/`),
		...[...authorSlugs].map((s) => `/authors/${s}/`)
	];

	const xml =
		'<?xml version="1.0" encoding="UTF-8"?>\n' +
		'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
		paths.map((p) => `  <url><loc>${SITE_URL}${p}</loc></url>`).join('\n') +
		'\n</urlset>\n';

	return new Response(xml, { headers: { 'content-type': 'application/xml' } });
}
