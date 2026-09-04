import { getSermon, listSermons } from '$lib/library-public';
import { getLang } from '$lib/lang.svelte';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

// Trailing-slash canonical -> prerenders to sermons/<slug>/index.html, which the
// static host serves as a directory index (see books/[slug] for the full note).
export const trailingSlash = 'always';
// A content-only merge (fixtures + cards) can race the API's seed: the web build
// prerenders whatever the API holds at build time, so new sermon pages ship as the
// SPA shell until the next build that touches frontend/. Tier 2 (#1418) did.

// Prerender one page per sermon — the slug list comes from the API at build
// time. The sermon endpoint may lag on a fresh deploy (api + web build together),
// so degrade to no sermon pages rather than fail the whole build; a later
// rebuild picks them up once the API is serving them.
export const entries: EntryGenerator = async () => {
	try {
		const sermons = await listSermons('en');
		return sermons.map((s) => ({ slug: s.slug }));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params }) => {
	const sermon = await orNotFound(() => getSermon(params.slug, getLang()));
	return { sermon };
};

// NOTE: prerendered per locale — the Spanish sermon translations (es) must be
// live on the API before the web build runs, else /es/sermons/<slug> bakes
// English and needs a fresh ochorus-web deploy once the API catches up.
