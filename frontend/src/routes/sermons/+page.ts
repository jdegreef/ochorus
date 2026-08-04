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
 *
 * Prerender refresh 2026-07-29 (queue job #477): the first Portuguese sermon —
 * A. B. Simpson's Himself (Ele Mesmo, PR #533) — went live, so the /pt/sermons
 * pages re-crawl and bake with the translated title.
 *
 * Prerender refresh 2026-07-30 (queue jobs #583/#584/#596/#555): four Portuguese
 * sermon translations ship — Moody's Os Oito "Eu Quero" de Cristo and Spurgeon's
 * A Primeira Oração de Paulo, O Clamor dos Corvos, and A Chave de Ouro da Oração
 * — so the /pt/sermons pages re-crawl and bake the new titles.
 *
 * Prerender refresh 2026-07-30 (queue job #606): the Swahili edition of Moody's
 * Eight "I Wills" of Christ ships — Ahadi Nane za "Nitafanya" za Kristo — so the
 * /sw/sermons pages re-crawl and bake the new title.
 *
 * Prerender refresh 2026-07-31 (queue jobs #631/#632/#633/#634): the FIRST
 * ARABIC SERMONS in the library — Spurgeon's عدم تغيّر الله (The Immutability of
 * God), Moody's حنان المسيح الذي لا حدّ له (Christ's Boundless Compassion),
 * Hudson Taylor's ينابيع لا تنضب (Unfailing Springs) and A. B. Simpson's
 * إمكانات الإيمان (The Possibilities of Faith). Arabic is RTL: the bodies carry
 * no dir/lang of their own, so /ar/sermons and each /ar/sermons/<slug> render
 * under the container's dir="auto" (see readerDirection.test.ts) and re-crawl
 * to bake the translated titles.
 *
 * Prerender refresh 2026-07-31 (queue jobs #672/#673/#674/#675): the FIRST
 * UKRAINIAN SERMONS — Spurgeon's Незмінність Бога, Moody's Безмежне милосердя
 * Христа and Христос — усе й у всьому, and A. B. Simpson's Він Сам. Ukrainian
 * is LTR, so no direction handling is needed; /uk/sermons and each
 * /uk/sermons/<slug> re-crawl and bake the translated titles. Note uk seeds as
 * status=draft, so these only matter once the language is launched from the
 * admin.
 *
 * Prerender refresh 2026-08-02 (PR #741): six sermons gained an "In brief" —
 * Spurgeon's Order and Argument in Prayer, The Ravens' Cry and Paul's First
 * Prayer, Moody's Christ All in All and Eight "I Wills" of Christ, and Hudson
 * Taylor's Unfailing Springs. #741 was backend-only (fixture rows plus the
 * translate_sermon fix), so Render SKIPPED the web build and the shelf kept
 * serving the old eight briefs while the api served fourteen — the brief is
 * baked into this prerendered page, so it needs a build that touches
 * `frontend/`. That is the whole job of this comment.
 *
 * Prerender refresh 2026-08-04 (PR #753): the LAST twelve English sermons
 * gained an "In brief", plus the eighteen translations that filling the
 * English side exposed. Same backend-only shape as #741, with one extra
 * wrinkle worth recording: a web build DID run just before this merge (for
 * #751/#752), so the entry-chunk hash changed and the deploy looked complete
 * — but that build raced ahead of this api release and baked the EMPTY
 * summaries. A changed chunk hash is therefore not evidence the shelf is
 * current; check for the brief TEXT in the served HTML instead.
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
