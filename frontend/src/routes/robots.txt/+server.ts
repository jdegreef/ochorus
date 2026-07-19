import { SITE_URL } from '$lib/config';

export const prerender = true;

export function GET() {
	const body = [
		'User-agent: *',
		'Allow: /',
		// Account/admin surfaces are blank SPA shells with nothing to index.
		'Disallow: /admin',
		'Disallow: /settings',
		'Disallow: /login',
		'Disallow: /account',
		'Disallow: /notebook',
		'Disallow: /reset-password',
		'',
		`Sitemap: ${SITE_URL}/sitemap.xml`,
		''
	].join('\n');
	return new Response(body, { headers: { 'content-type': 'text/plain' } });
}
