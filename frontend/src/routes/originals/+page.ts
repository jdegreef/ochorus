import { getOriginals } from '$lib/library-public';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

export const prerender = true;
// Prerenders to originals/index.html; `localizeHref` emits the slash form
// (SLASHED_PAGES in $lib/href), so every locale's copy is served without a
// Render rewrite. The crawler reaches /<locale>/originals/ from the footer.
export const trailingSlash = 'always';

// Per locale: the imprint's books in this language only (no English fallback).
// Caught rather than thrown, as loadShelf does, so a web build that runs ahead
// of the API release bakes the error panel instead of failing — and the panel's
// Try again re-runs this against the live API.
export const load: PageLoad = async ({ fetch }) => {
	try {
		return { shelf: await getOriginals(getLang(), fetch), loadError: false };
	} catch {
		return { shelf: { books: [], series: [], languages: [] }, loadError: true };
	}
};
