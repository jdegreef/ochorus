import { listPlans } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

/**
 * Prerender refresh 2026-08-05 (queue job #652, follow-up to PR #834): the
 * Arabic prose for "Humility in 12 Days" (التواضع في اثني عشر يومًا) landed.
 * The row itself already existed — PR #819 published the Arabic Humility, and
 * seed_plans creates a Plan per published language of a LAUNCH_PLANS source
 * book, falling back to the ENGLISH tuple when PLAN_TRANSLATIONS has no entry.
 * So /ar/plans has been serving an English-titled card; this touch re-crawls it
 * so the static page bakes the Arabic title and description.
 *
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
 *
 * Prerender refresh 2026-07-23 (day-one teaser, PR #371): PlanListSerializer
 * gained a `day_one` field, but the web build raced the api and prerendered
 * /plans before it was served, so the baked cards lack the "Day 1 · book —
 * chapter" line (hydration adds it; first paint and no-JS don't). This touch
 * re-crawls once the field is live. Verified 8/8 plans return day_one.
 *
 * Prerender refresh 2026-07-29 (queue job #492): A Month in the Inner Chamber
 * gained its Portuguese prose (Um Mês na Câmara Interior, PR #533). The pt plan
 * row was auto-created when The Inner Chamber shipped in pt and had been
 * falling back to the English title, so /pt/plans re-crawls and bakes it.
 *
 * Prerender refresh 2026-08-05 (queue job #630): A School of Prayer becomes
 * Arabic — مدرسة الصلاة, 27 days. Its three source books (#754, #755, #729)
 * shipped in Arabic in the same change, which is what lets seed_plans create
 * the plan at all: it only creates one in a language where EVERY source book
 * exists. So /ar/plans re-crawls to bake the new card. Portuguese is the
 * counter-example still pending — it has the PLAN_TRANSLATIONS prose but not
 * all three books, so no pt row is created and /pt/plans is unchanged.
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
