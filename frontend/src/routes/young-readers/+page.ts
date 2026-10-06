import { getAudienceShelf, type AudienceShelf } from '$lib/library-public';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

// A young-reader hub ($lib/audienceHub) — a browse shelf on the /series model.
// Prerenders to /young-readers/index.html, so its links carry the slash (href.ts
// isSlashedPath) and the crawler reaches every localized copy from the footer.
export const prerender = true;
export const trailingSlash = 'always';

const EMPTY: AudienceShelf = {
	audience: 'young_readers',
	series: [],
	editions: [],
	more: [],
	plans: [],
	topic: null,
	printable: [],
	languages: []
};

export const load: PageLoad = async ({ fetch }) => {
	// Caught, not thrown — the loadShelf rule: a lagging API must not fail the
	// build, and the page reports the failure with Try again rather than
	// claiming an empty shelf.
	try {
		return { shelf: await getAudienceShelf('young_readers', getLang(), fetch), loadError: false };
	} catch {
		return { shelf: EMPTY, loadError: true };
	}
};
