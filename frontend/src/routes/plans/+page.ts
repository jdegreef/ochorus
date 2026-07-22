import { listPlans } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

/**
 * Prerender refresh 2026-07-22 (queue jobs #272/#286): the Swahili prose for
 * "A School of Prayer" (Shule ya Maombi) landed, and the Luganda prose
 * (Essomero ery'Okusaba) is already in place. seed_plans only materializes the
 * localized Plan row once all three source books are published in that
 * language, so this touch forces an ochorus-web rebuild so the /lg|/sw plans
 * pages re-crawl and bake the translated title/description as each language's
 * book set completes.
 *
 * Prerender refresh 2026-07-22 (School of Prayer now live in lg + sw): the last
 * missing source books shipped (PR #351), so seed_plans now materializes both
 * localized rows — Essomero ery'Okusaba (lg) and Shule ya Maombi (sw), 27 days
 * each. This touch re-crawls /lg/plans and /sw/plans so the plan cards appear.
 *
 * Prerender refresh 2026-07-22 (five new curated plans): added The Deeper Life,
 * The Way to God, The God of All Comfort (also live in lg), Power from on High,
 * and Everything for Christ — all English-first, materializing per language as
 * their source books get translated. This touch bakes the new /plans cards.
 *
 * Prerender refresh 2026-07-22 (Power from on High now live in es/lg/sw): the
 * second source book (Torrey's Holy Spirit, PR #365) shipped in all three
 * languages, so seed_plans now materializes the plan everywhere with localized
 * prose. This touch re-crawls /es|/lg|/sw/plans so the plan card appears.
 */
export const load: PageLoad = async () => {
	// Tolerate a lagging/absent plans endpoint at prerender time (api + web can
	// build together on a deploy) — render an empty list rather than fail the
	// build; a later rebuild picks the plans up.
	try {
		return { plans: await listPlans(getLang()) };
	} catch {
		return { plans: [] };
	}
};
