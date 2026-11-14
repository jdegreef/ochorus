import { isHttpError } from '@sveltejs/kit';
import {
	getBibleLinks,
	getSeries,
	listPlans,
	type BibleBookLinks,
	type PlanSummary,
	type SeriesDetail
} from '$lib/library-public';
import { BIBLE_SERIES, biblePlans } from '$lib/bible';
import { orNotFound } from '$lib/loadHelpers';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

// Prerenders to bible/index.html (isSlashedPath), reached by the English
// footer's More column. Only the locales in BIBLE_LOCALES link it, so the
// crawl bakes no copy where there is no Bible to show.
export const prerender = true;
export const trailingSlash = 'always';

export const load: PageLoad = async ({ fetch }) => {
	const lang = getLang();
	// The primary list is the `the-bible` series. In a language with no Bible
	// book the API 404s (no English fallback) and orNotFound turns that into the
	// not-found page, as a series page does — never English books at a
	// localized URL. English is where the hub always exists, so there any
	// failure (a 404 included: a web build that runs ahead of the API release
	// that seeds the series) bakes the error panel instead of failing the build,
	// and its Try again re-runs this against the live API (loadShelf's reason).
	// The plans and the per-book links (sermons, the classics) are decoration:
	// each has its own silent catch, costing only what it draws.
	const fetchSeries = () => getSeries(BIBLE_SERIES, lang);
	const [result, plans, links] = await Promise.all([
		(lang === 'en' ? fetchSeries() : orNotFound(fetchSeries)).then(
			(series): { series: SeriesDetail | null; loadError: boolean } => ({ series, loadError: false }),
			(e) => {
				if (isHttpError(e)) throw e;
				return { series: null, loadError: true };
			}
		),
		listPlans(lang, fetch).catch((): PlanSummary[] => []),
		getBibleLinks(lang, fetch).catch((): BibleBookLinks[] => [])
	]);
	return {
		...result,
		plans: result.series ? biblePlans(plans) : [],
		links
	};
};
