import { error } from '@sveltejs/kit';
import { bibleIn } from '$lib/bible';
import { STORY_BOOK, STORY_PLAN_SLUG } from '$lib/bibleStory';
import { getBook, listPlans } from '$lib/library-public';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

// The Bible walked in story order ($lib/bibleStory). Prerenders to
// bible/story/index.html (isSlashedPath), reached from the /bible hub. Its
// prose is English, like the hub's own copy: a language with no Bible has no
// page (BIBLE_LOCALES), as it has no hub, so nothing links it there and the
// crawl never bakes one. The story itself is data; the only requests ask
// whether its two "Read on" links exist here — the plan and the teens book —
// so the page never links one the API does not serve (the prerender crawl
// fails on a link to a 404). Either failing costs only its card.
export const prerender = true;
export const trailingSlash = 'always';

export const load: PageLoad = async ({ fetch }) => {
	const lang = getLang();
	if (!bibleIn(lang)) error(404, 'Not found');
	const [plan, book] = await Promise.all([
		listPlans(lang, fetch).then(
			(plans) => plans.some((p) => p.slug === STORY_PLAN_SLUG),
			() => false
		),
		getBook(STORY_BOOK.slug, lang, fetch).then(
			(b) => b.language === lang,
			() => false
		)
	]);
	return { plan, book };
};
