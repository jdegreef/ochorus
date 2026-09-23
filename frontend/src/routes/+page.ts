import { building } from '$app/environment';
import { listBooks } from '$lib/library-public';
import { shelf, type HomeShelves } from '$lib/homeShelves';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

/** What the page shows when the snapshot cannot be read at runtime: the shelf
 *  sections hide themselves when empty, so this reads as a shorter page. */
const EMPTY: HomeShelves = {
	featured: [],
	authors: [],
	topics: [],
	counts: { books: 0, authors: 0, sermons: 0 }
};

// NOTE: this page is prerendered — only PUBLIC data belongs here. Personal
// blocks (Continue reading, Today's reading) fetch client-side in their
// components so the baked HTML is the same for everyone.
export const load: PageLoad = async ({ fetch }) => {
	const lang = getLang();
	const [shelves, books] = await Promise.all([
		// The public shelves come from the build's snapshot, read through
		// SvelteKit's `fetch` so the response is inlined into the prerendered
		// HTML and REPLAYED at hydration — the browser renders exactly the items
		// the HTML holds. See `$lib/homeShelves` for what went wrong without it.
		// Loud while building (an empty front page must not ship), degraded at
		// runtime (see `shelf`).
		fetch(`/home-shelves/${lang}.json`)
			.then((res) => {
				if (!res.ok) throw new Error(`home shelves: ${res.status}`);
				return res.json() as Promise<HomeShelves>;
			})
			.catch((err) => {
				if (building) throw err;
				return EMPTY;
			}),
		// The full live list, for the PERSONAL blocks only (Continue reading,
		// Recommended next, the signup band's resume line) — none of which is in
		// the prerendered HTML, so it cannot disagree with it. Unfiltered, so a
		// returning reader still lands on their own book, plate cover or not.
		shelf(listBooks(lang))
	]);
	return { books, ...shelves };
};
