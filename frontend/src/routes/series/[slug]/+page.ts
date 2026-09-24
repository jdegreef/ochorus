import { getSeries, listSeries } from '$lib/library-public';
import { orNotFound } from '$lib/loadHelpers';
import { getLang } from '$lib/lang.svelte';
import type { EntryGenerator, PageLoad } from './$types';

// Prerendered like topics: one entry per English series. The localized pages
// are discovered by the crawler through each localized book page's series line,
// which links here — the same way localized topic and chapter pages are found.
export const trailingSlash = 'always';

export const entries: EntryGenerator = async () => {
	try {
		const series = await listSeries('en');
		return series.map((s) => ({ slug: s.slug }));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params }) => {
	// A series with no name or no book in this language 404s in the API (no
	// English fallback), and orNotFound turns that into the not-found page.
	return { series: await orNotFound(() => getSeries(params.slug, getLang())) };
};
