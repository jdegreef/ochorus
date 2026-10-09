import { building } from '$app/environment';
import { error } from '@sveltejs/kit';
import { EMPTY_SHELF_DATA, FOR_PAGES, forPage, isShelfData } from '$lib/forPages';
import type { EntryGenerator, PageLoad } from './$types';

// The "Ochorus for …" pages ($lib/forPages): English-only, one per group.
// Prerenders to /for/<group>/index.html, so links carry the slash
// (isSlashedPath).
export const prerender = true;
export const trailingSlash = 'always';

export const entries: EntryGenerator = () => FOR_PAGES.map((p) => ({ group: p.slug }));

export const load: PageLoad = async ({ params, fetch }) => {
	const page = forPage(params.group);
	if (!page) error(404, 'Not found');
	// The shelves, plans, guides and offline pack are the build's snapshot
	// (routes/for-shelves), the home page's pattern: loud while building, so a
	// page cannot ship without its books looking deliberate; quiet at runtime,
	// where a missing file (the SPA fallback answers 200 with HTML, which
	// `json()` rejects) or an offline reader just gets the page without them.
	try {
		const res = await fetch(`/for-shelves/${page.slug}.json`);
		if (!res.ok) throw new Error(`for-shelves/${page.slug}: ${res.status}`);
		const shelf: unknown = await res.json();
		// A cached copy from before the snapshot was an object would otherwise
		// reach the page as an array and break it.
		if (!isShelfData(shelf)) throw new Error(`for-shelves/${page.slug}: not a snapshot`);
		// Over the empty one, so a snapshot from before a section existed
		// (a cached copy of the last release) still has every field.
		return { page, shelf: { ...EMPTY_SHELF_DATA, ...shelf } };
	} catch (err) {
		if (building) throw err;
		return { page, shelf: EMPTY_SHELF_DATA };
	}
};
