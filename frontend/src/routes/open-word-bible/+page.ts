import { error } from '@sveltejs/kit';
import { getSeries, type SeriesDetail } from '$lib/library-public';
import { BIBLE_SERIES, bibleIn } from '$lib/bible';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

// The page about the translation the library's Bible is printed in, in place
// of an author page (see $lib/openWordBible). Prerenders to
// open-word-bible/index.html (isSlashedPath). Its prose is English, like the
// Bible it describes: a language with no Bible has no page (BIBLE_LOCALES),
// as it has no hub.
export const prerender = true;
export const trailingSlash = 'always';

export const load: PageLoad = async () => {
	const lang = getLang();
	if (!bibleIn(lang)) error(404, 'Not found');
	// The series lends the page its covers and its count. Decoration: a read
	// that fails (an API behind this build) costs the fan, never the page.
	const series = await getSeries(BIBLE_SERIES, lang).catch((): SeriesDetail | null => null);
	return { series };
};
