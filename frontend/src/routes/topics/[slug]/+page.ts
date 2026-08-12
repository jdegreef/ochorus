import { getTopic, listTopics } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { EntryGenerator, PageLoad } from './$types';

// Trailing-slash canonical -> prerenders to topics/<slug>/index.html, which the
// static host serves as a directory index (see books/[slug] for the full note).
// Prerender refresh 2026-08-10: re-bake /topics after the four new shelves
// (the-gospel-call, enduring-classics, the-way-of-holiness,
// the-preached-word) seeded — the same-deploy web build can prerender
// before seed_topics runs, so this trailing touch forces the rebuild that
// actually sees them.
export const trailingSlash = 'always';

// Prerender one page per topic — the slug list comes from the API at build
// time. The topics endpoint may lag on a fresh deploy (api + web build
// together), so degrade to no topic pages rather than fail the whole build;
// a later rebuild picks them up once the API is serving them.
export const entries: EntryGenerator = async () => {
	try {
		const topics = await listTopics('en');
		return topics.map((tp) => ({ slug: tp.slug }));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params }) => {
	return { topic: await getTopic(params.slug, getLang()) };
};
