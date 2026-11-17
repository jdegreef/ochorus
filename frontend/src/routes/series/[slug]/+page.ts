import { getSeries, listSeries, type SeriesSummary } from '$lib/library-public';
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

export const load: PageLoad = async ({ params, fetch }) => {
	const lang = getLang();
	// A series with no name or no book in this language 404s in the API (no
	// English fallback), and orNotFound turns that into the not-found page. The
	// "More book series" row is decoration: its own silent catch, so a failed
	// list costs the row and never the page.
	const [series, all] = await Promise.all([
		// Load's own fetch, so the response is inlined in the prerendered page:
		// scripts/build-series-cards.mjs draws the share card from it.
		orNotFound(() => getSeries(params.slug, lang, fetch)),
		listSeries(lang, fetch).catch((): SeriesSummary[] => [])
	]);
	// Same audience first (a parent on Brave for God sees the other young
	// series before the adult ones); the index's own order otherwise (sort is stable).
	const same = (s: SeriesSummary) => (s.audience && s.audience === series.audience ? 0 : 1);
	const others = all
		.filter((s) => s.slug !== params.slug)
		.sort((a, b) => same(a) - same(b))
		.slice(0, 4);
	return { series, others };
};
