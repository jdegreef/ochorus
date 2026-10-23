import { building } from '$app/environment';
import type { HomeShelves } from '$lib/homeShelves';
import { readHomeSnapshot } from '$lib/homeSnapshot';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

/** What the page shows when the snapshot cannot be read at runtime: the shelf
 *  sections hide themselves when empty, so this reads as a shorter page. */
const EMPTY: HomeShelves = {
	featured: [],
	authors: [],
	topics: [],
	counts: { books: 0, authors: 0, sermons: 0 },
	audiences: []
};

// NOTE: this page is prerendered — only PUBLIC data belongs here. Personal
// blocks (Continue reading, Recommended next, the signup band) fetch
// client-side in their components, and only when the reader has progress, so
// the baked HTML is the same for everyone and hydration waits on nothing live.
export const load: PageLoad = async ({ fetch }) => {
	// The public shelves come from the build's snapshot (`readHomeSnapshot`), so
	// the browser renders exactly the items the HTML holds. See `$lib/homeShelves`
	// for what went wrong without it, and for why a client-side navigation home
	// shows the build's shelves too.
	//
	// Loud while building: a front page with empty shelves must not ship
	// looking deliberate. Degraded at runtime: a reader who is offline, or a
	// locale whose file is missing (the SPA fallback answers 200 with HTML,
	// which `json()` rejects), gets a shorter page, not a full-page error.
	try {
		return await readHomeSnapshot(fetch, getLang());
	} catch (err) {
		if (building) throw err;
		return EMPTY;
	}
};
