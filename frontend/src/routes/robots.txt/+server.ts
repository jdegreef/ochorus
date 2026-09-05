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
		// NO blank line before the next block: a blank line TERMINATES a record
		// in robots.txt, so anything after one belongs to no user-agent. The
		// rules below have to stay inside the `User-agent: *` group above.
		//
		// The domain ran a WordPress site before this app, and Googlebot is
		// still working through its corpse: /wp-content/ PDFs, /wp-includes/
		// scripts and ?p= post ids make up nearly all of "Crawled - currently
		// not indexed". None of it exists any more, every one of them answers
		// 200 with the SPA shell (the /* -> /200.html catch-all), and each
		// fetch is crawl budget NOT spent on the 1,890 chapter pages that are
		// the actual reason this site should rank.
		'Disallow: /wp-content/',
		'Disallow: /wp-includes/',
		'Disallow: /wp-admin/',
		'Disallow: /wp-json/',
		'Disallow: /*?p=',
		'Disallow: /*/feed/',
		'',
		`Sitemap: ${SITE_URL}/sitemap.xml`,
		// The Atom feed is discovered via the <link rel="alternate"> in the app
		// shell, not here: `Feed:` is not a robots.txt directive, so a validator
		// (and Lighthouse) flags the file as invalid, which risks the whole file
		// being distrusted. Leave it as a comment for a human reader only.
		`# Feed: ${SITE_URL}/feed.xml`,
		''
	].join('\n');
	return new Response(body, { headers: { 'content-type': 'text/plain' } });
}
