import { error, isHttpError } from '@sveltejs/kit';
import { BIBLE_SERIES, bibleIn } from '$lib/bible';
import { BIBLE_PATHS } from '$lib/bibleHub';
import { getSeries } from '$lib/library-public';
import { getLang } from '$lib/lang.svelte';
import type { EntryGenerator, PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

/**
 * One page per "Where to start" path (`BIBLE_PATHS`): the hub's switcher shows
 * a path in place, but a tab inside a hub can't answer "Bible chapters for
 * grief", and a page can. The localized copies are reached the way the story
 * page's are, by the hub's own links in each hub locale.
 */
export const entries: EntryGenerator = () => BIBLE_PATHS.map((p) => ({ path: p.slug }));

export const load: PageLoad = async ({ params, fetch }) => {
	const lang = getLang();
	const path = BIBLE_PATHS.find((p) => p.slug === params.path);
	if (!path || !bibleIn(lang)) error(404, 'Not found');
	try {
		const series = await getSeries(BIBLE_SERIES, lang, fetch);
		return {
			pathId: path.id,
			books: series.books,
			languages: series.available_languages.filter(bibleIn) as string[]
		};
	} catch (e) {
		if (isHttpError(e)) throw e;
		error(404, 'Not found');
	}
};
