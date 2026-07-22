import { listSermons } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

/**
 * Prerender refresh 2026-07-17 (queue job #180): force an ochorus-web rebuild
 * after the api went live with the Luganda sermon Enteekateeka n'Ensonga mu
 * Kusaba (PR #186), so the /lg/sermons pages re-crawl and bake the new title.
 *
 * Prerender refresh 2026-07-17 (queue job #181): same again after the Luganda
 * sermon Ekisumuluzo ekya Zaabu eky'Okusaba (PR #188) went live.
 *
 * Prerender refresh 2026-07-18 (queue job #182): same again after the Luganda
 * sermon Ebisoboka by'Okukkiriza (PR #191) went live.
 *
 * Prerender refresh 2026-07-18 (queue job #183): same again after the Luganda
 * sermon Kristo Byonna mu Byonna (PR #193) went live.
 *
 * Prerender refresh 2026-07-20 (queue job #249): same again after the Luganda
 * edition of Spurgeon's sermon Free Grace (Ekisa eky'Obwereere, PR #266) went
 * live, so the /lg/sermons pages re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-20 (queue job #250): same again after the Luganda
 * edition of A. B. Simpson's sermon The Joy of the Lord (Essanyu lya Mukama,
 * PR #268) went live, so the /lg/sermons pages re-crawl and bake with the new
 * title.
 *
 * Prerender refresh 2026-07-21 (queue job #251): same again after the Luganda
 * edition of D. L. Moody's sermon Eight "I Wills" of Christ ('Ndikola' Munaana
 * eza Kristo, PR #277) went live, so the /lg/sermons pages re-crawl and bake
 * with the new title.
 *
 * Prerender refresh 2026-07-22 (queue job #282): same again after the Swahili
 * edition of Hudson Taylor's sermon Unfailing Springs (Chemchemi Zisizokauka,
 * PR #335) went live, so the /sw/sermons pages re-crawl and bake with the new
 * title.
 *
 * Prerender refresh 2026-07-22 (queue job #283): same again after the Swahili
 * edition of A. B. Simpson's sermon Himself (Yeye Mwenyewe, PR #336) went
 * live, so the /sw/sermons pages re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-22 (queue job #284): same again after the Swahili
 * edition of D. L. Moody's sermon Christ's Boundless Compassion (Huruma
 * Isiyo na Kikomo ya Kristo, PR #338) went live, so the /sw/sermons pages
 * re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-22 (queue job #285): same again after the Swahili
 * edition of C. H. Spurgeon's sermon The Immutability of God (Kutobadilika
 * kwa Mungu, PR #340) went live, so the /sw/sermons pages re-crawl and bake
 * with the new title.
 */
export const load: PageLoad = async () => {
	// Tolerate a lagging/absent sermon endpoint at prerender time (see the
	// [slug] entries generator) — render an empty list rather than fail the build.
	try {
		return { sermons: await listSermons(getLang()) };
	} catch {
		return { sermons: [] };
	}
};
