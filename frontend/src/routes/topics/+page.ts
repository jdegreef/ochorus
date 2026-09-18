import { listTopics } from '$lib/library-public';
import { loadShelf } from '$lib/loadShelf';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

// Prerender refresh 2026-09-18: French topic translations for for-teens
// (« Pour les adolescents ») and for-young-readers (« Pour les jeunes
// lecteurs ») land in data/topic_translations/fr.json (#2502, #2503), so
// seed_topics now titles those two fr shelves in French; this touch re-bakes
// /fr/topics and their /fr/topics/<slug> pages so the localized title,
// description and Segond epigraph appear instead of the English fallback.
// Prerender refresh 2026-07-16: re-bake /topics and /topics/<slug> after the
// api went live with the topic scripture epigraphs + sermon memberships, so the
// prerendered pages pick up the accent/verse/"N books · M sermons" and the
// Sermons section (a same-deploy web build can prerender before seed_topics).
// Prerender refresh 2026-08-10: re-bake /topics after the four new shelves
// (the-gospel-call, enduring-classics, the-way-of-holiness,
// the-preached-word) seeded — the same-deploy web build can prerender
// before seed_topics runs, so this trailing touch forces the rebuild that
// actually sees them.
export const load: PageLoad = async () => {
	const { items, loadError } = await loadShelf(listTopics(getLang()));
	return { topics: items, loadError };
};
