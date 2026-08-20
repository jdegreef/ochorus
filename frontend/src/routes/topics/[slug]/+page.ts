import { getTopic, listTopics } from '$lib/library';
import { orNotFound } from '$lib/loadHelpers';
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

// Prerender refresh 2026-08-19 (queue jobs #799 #800 #801 #802 #847 #848 #894
// #895 #945 #946 #947 #948, PR #993): the Ukrainian shelf prose — all ten
// topics at once, because topic prose has no English fallback and a partial
// file leaves shelves HIDDEN rather than untranslated. Before this, every
// /uk/topics/<slug> page 404'd; they now render, so the built pages have to be
// re-baked. uk seeds status=draft, so they stay out of the sitemap until the
// language is switched live — which is the point of touching this now rather
// than at launch.
//
// Prerender refresh 2026-08-19 (queue jobs #701 #702 #703 #844 #845 #846 #994
// #995 #996 #997, PR #998): the Hindi shelf prose, all ten topics, same
// all-or-nothing reason as the Ukrainian set above. Four of the ten had never
// been filed, so the set was unshippable until this run queued them. Every
// /hi/topics/<slug> page 404'd before this and now renders. hi seeds
// status=draft like uk, so they stay out of the sitemap until the language is
// switched live.
//
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
	// orNotFound turns the API's 404 into SvelteKit's, so an unpublished or
	// mistyped slug gets the not-found page (with its daily picks) instead of the
	// generic "something went wrong — try again" shell, which offers a retry for
	// a page that will never exist. Books, chapters, sermons and authors have
	// always done this; topics and plans were the two that missed it.
	return { topic: await orNotFound(() => getTopic(params.slug, getLang())) };
};
