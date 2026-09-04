// prerender refresh 2026-09-04: Hindi plan prose completed — grace-for-every-sinner
// (#1108) and faith-in-the-fire (#1444) added to data/plan_translations/hi.json,
// which finishes the Hindi set. Both are DORMANT (a curated plan needs every source
// book in the language, and a-call-to-the-unconverted / the-god-of-all-comfort have
// no Hindi edition yet), so this touch is not for them — it rebuilds /hi/plans for
// the three entries that were already shipped but never had their prerender
// follow-up done: school-of-prayer (#1107), humility-12-days (#1126) and
// deeper-life-in-christ (#1127). humility-12-days is the live one.
// prerender refresh 2026-08-28: humility-12-days.hi (job #1103).
// humility-2 is that plan's ONE source book, so shipping the hi edition
// publishes the plan for hi and this shelf has a new card to bake. The two
// other books in the same PR (all-of-grace.hi, the-way-to-god.hi) feed no
// plan at all and owe only the books/ touch.
import { listPlans } from '$lib/library-public';
import { loadShelf } from '$lib/loadShelf';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

/**
 * Prerender refresh 2026-08-19 (queue jobs #690 + #843): the-inner-chamber
 * ships in Hindi, and it is the sole source book of the-inner-chamber-month, so
 * seed_plans creates that plan row in hi on this deploy. Without this touch the
 * DB would carry the plan and /hi/plans would keep serving the page it was
 * built with — the fix landing invisibly, which reads as the fix not working.
 * The plan prose (PLAN_TRANSLATIONS["hi"]) is in the same commit.
 *
 * Prerender refresh 2026-08-17 (queue job #594, PR #964): the Portuguese
 * Humildade ships, and seed_plans creates "Humildade em 12 Dias" from prose
 * that was already in PLAN_TRANSLATIONS — the plan did not exist in pt before
 * this deploy, so /pt/plans must re-crawl to list it.
 *
 * Prerender refresh 2026-08-14 (queue jobs #519/#520, PR #942): the Spanish
 * Humility ships with its plan prose, so seed_plans creates "Humildad en 12
 * Días" and /es/plans must re-crawl to show the translated card instead of
 * nothing (the plan did not exist in es before this deploy).
 *
 * Prerender refresh 2026-08-08 (follow-up to PR #881): the es and uk prose for
 * "A Month in the Inner Chamber" landed — «Un mes en el aposento interior» and
 * «Місяць у внутрішній кімнаті». Same defect and same shape as the sw entry
 * below, which was the one noticed first; a sweep of every plan x language pair
 * then found these two were the only others, and #881 added the test that stops
 * the class recurring.
 *
 * Prerender refresh 2026-08-08 (queue job #422, follow-up to PR #878): the
 * Swahili prose for "A Month in the Inner Chamber" (Mwezi katika Chumba cha
 * Ndani) landed. Same shape as the Arabic Humility entry below — the sw row
 * already existed, because `the-inner-chamber` is published in Swahili and
 * seed_plans creates a Plan per published language of a LAUNCH_PLANS source
 * book, falling back to the ENGLISH tuple when PLAN_TRANSLATIONS has none. So
 * /sw/plans has been serving an English-titled card; this touch re-crawls it so
 * the static page bakes the Swahili title and description.
 *
 * The same job's other entry, `deeper-life-in-christ`, needs no refresh yet:
 * two of its three source books are still English-only, so seed_plans does not
 * materialize the sw row at all. That card arrives with whichever of
 * `the-masters-indwelling` / `union-and-communion` lands second, and THAT is
 * the commit which needs the touch.
 *
 * Prerender refresh 2026-08-06 (queue job #756, follow-up to PR #855): the
 * Arabic "The God of All Comfort" landed, which was the last source book
 * `faith-in-the-fire` needed in ar — `he-holds-my-tomorrows` was already there.
 * So seed_plans now materializes the (faith-in-the-fire, ar) row, 35 days across
 * the two books, with the Arabic prose #855 added alongside the book. This touch
 * re-crawls /ar/plans so the new card appears with its translated title.
 *
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
 *
 * Prerender refresh 2026-08-05 (queue job #418, the plan side-effect): Andrew
 * Murray's Humility shipped in Swahili, and it is the sole source book of
 * humility-12-days — so seed_plans now creates that plan in sw and /sw/plans
 * re-crawls to bake the new card. It was created with the English title, since
 * a row falls back to the English tuple when PLAN_TRANSLATIONS has no entry.
 *
 * Prerender refresh 2026-08-05 (queue job #421): and now that row's Swahili
 * prose — Unyenyekevu kwa Siku 12. "The root of every virtue" is «mzizi wa kila
 * wema», taken verbatim from the Swahili edition of the book the plan sends
 * readers to, so the card and the book agree. /sw/plans re-crawls again.
 */
export const load: PageLoad = async () => {
	const { items, loadError } = await loadShelf(listPlans(getLang()));
	return { plans: items, loadError };
};
