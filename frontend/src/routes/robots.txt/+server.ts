import { SITE_URL } from '$lib/config';

export const prerender = true;

export function GET() {
	const body = `User-agent: *\nAllow: /\n\nSitemap: ${SITE_URL}/sitemap.xml\n`;
	return new Response(body, { headers: { 'content-type': 'text/plain' } });
}
