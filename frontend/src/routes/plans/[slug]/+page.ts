import { getPlan, listPlans } from '$lib/library-public';
import { orNotFound } from '$lib/loadHelpers';
import { getLang } from '$lib/lang.svelte';
import type { EntryGenerator, PageLoad } from './$types';

// Trailing-slash canonical -> prerenders to plans/<slug>/index.html, which the
// static host serves as a directory index (see books/[slug] for the full note).
export const trailingSlash = 'always';

// Prerender one page per plan — the slug list comes from the API at build
// time. The plans endpoint may lag on a fresh deploy (api + web build
// together), so degrade to no plan pages rather than fail the whole build;
// a later rebuild picks them up once the API is serving them. Note: a plan
// added by a backend-only change (plan_seed.py) skips the web build entirely
// (Render only builds web when a frontend/ file changed), so its page needs
// one forced web rebuild to prerender — see the deploy skill.
export const entries: EntryGenerator = async () => {
	try {
		const plans = await listPlans('en');
		return plans.map((p) => ({ slug: p.slug }));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params }) => {
	// See the note in topics/[slug]: an unknown slug must reach the not-found
	// page, not the generic retry shell.
	return { plan: await orNotFound(() => getPlan(params.slug, getLang())) };
};
