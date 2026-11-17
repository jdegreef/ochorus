import { error } from '@sveltejs/kit';
import { bibleIn } from '$lib/bible';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

// The Bible walked in story order ($lib/bibleStory). Prerenders to
// bible/story/index.html (isSlashedPath), reached from the /bible hub. Its
// prose is English, like the hub's own copy: a language with no Bible has no
// page (BIBLE_LOCALES), as it has no hub, so nothing links it there and the
// crawl never bakes one. It needs no request: the story is data.
export const prerender = true;
export const trailingSlash = 'always';

export const load: PageLoad = () => {
	if (!bibleIn(getLang())) error(404, 'Not found');
};
