import { building } from '$app/environment';
import { error } from '@sveltejs/kit';
import { forLocale } from '$lib/forLinks';
import { EMPTY_SHELF_DATA, FOR_PAGES, forPage, isShelfData } from '$lib/forPages';
import { buildForShelf } from '$lib/forShelves';
import { getLang } from '$lib/lang.svelte';
import { IS_APP } from '$lib/platform';
import type { EntryGenerator, PageLoad } from './$types';

// The "Ochorus for …" pages ($lib/forPages): one per group, in English and
// French (a reader in any other locale is shown the English page). Prerenders
// to [/fr]/for/<group>/index.html, so links carry the slash (isSlashedPath);
// the French copies are reached by the crawl from the French footer.
export const prerender = true;
export const trailingSlash = 'always';

export const entries: EntryGenerator = () => FOR_PAGES.map((p) => ({ group: p.slug }));

export const load: PageLoad = async ({ params, fetch }) => {
	const locale = forLocale(getLang());
	const page = forPage(params.group, locale);
	if (!page) error(404, 'Not found');
	// The shelves, plans, guides and offline pack are the build's snapshot
	// (routes/for-shelves), the home page's pattern: loud while building, so a
	// page cannot ship without its books looking deliberate; quiet at runtime,
	// where a missing file (the SPA fallback answers 200 with HTML, which
	// `json()` rejects) or an offline reader just gets the page without them.
	// The app has no snapshot (it prerenders nothing), so it derives the same
	// data from the live API the way the snapshot's endpoint does at build.
	const file = locale === 'en' ? `/for-shelves/${page.slug}.json` : `/for-shelves/${locale}/${page.slug}.json`;
	try {
		if (IS_APP) return { page, locale, shelf: await buildForShelf(page, locale, fetch) };
		const res = await fetch(file);
		if (!res.ok) throw new Error(`${file}: ${res.status}`);
		const shelf: unknown = await res.json();
		// A cached copy from before the snapshot was an object would otherwise
		// reach the page as an array and break it.
		if (!isShelfData(shelf)) throw new Error(`${file}: not a snapshot`);
		// Over the empty one, so a snapshot from before a section existed
		// (a cached copy of the last release) still has every field.
		return { page, locale, shelf: { ...EMPTY_SHELF_DATA, ...shelf } };
	} catch (err) {
		if (building) throw err;
		return { page, locale, shelf: EMPTY_SHELF_DATA };
	}
};
