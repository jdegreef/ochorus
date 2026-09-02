// prerender refresh 2026-09-02 (batch2): three new sw sermons — blessed-adversity
// (Hudson Taylor, #867), salvation-by-faith (Wesley, #868), the-dying-thief
// (Moody, #869). Rebuilds the /sw/sermons shelf.
// prerender refresh 2026-09-02: five new sermon editions — rest.sw & rest.lg
// (Moody, jobs #1303/#1216), pauls-first-prayer.lg (Spurgeon, #1215),
// salvation-by-faith.lg (Wesley, #1214), aggressive-christianity.lg (Booth,
// #1213). Rebuilds the localized /sw/sermons and /lg/sermons shelves.
// prerender refresh 2026-08-21: the-joy-of-the-lord.pt (job #775, PR #1008)
// prerender refresh 2026-08-20: himself.hi (job #700, PR #1004)
import { listSermons } from '$lib/library-public';
import { loadShelf } from '$lib/loadShelf';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

/**
 * Prerender refresh 2026-08-17 (queue jobs #697-#699, PR #964): the library's
 * first Hindi sermons — परमेश्वर की अपरिवर्तनीयता, मसीह की असीम करुणा and
 * कभी न सूखनेवाले सोते. hi seeds status=draft, so /hi/sermons is built but not
 * advertised (no hi URLs in the sitemap); this touch means the pages are
 * already baked when the admin launches the language, rather than needing a
 * deploy after the switch.
 *
 * Prerender refresh 2026-08-14 (queue jobs #553/#771-#774, PR #942): five
 * Portuguese sermons — As Possibilidades da Fé, Ordem e Argumento na Oração,
 * Descanso, Bendita Adversidade, O Novo Nascimento. /pt/sermons re-crawls the
 * cards and detail pages with localized scripture_refs and summaries.
 *
 * Prerender refresh 2026-08-10 (queue jobs #527/#528/#529, PR #931): three
 * Swahili sermons landed at once — Furaha ya Bwana (Simpson), Ufunguo wa
 * Dhahabu wa Maombi and Utaratibu na Hoja katika Maombi (Spurgeon). Re-crawl
 * /sw/sermons so the cards and detail pages bake the translated titles,
 * localized scripture_refs and "In brief" summaries.
 *
 * Prerender refresh 2026-08-08 (queue job #424, PR #901): Moody's "Christ All
 * in All" landed in Swahili as Kristo Yote katika Yote. Re-crawl /sw/sermons so
 * the card and its /sw/sermons/christ-all-in-all page bake the translated title
 * and the "In brief" summary.
 *
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
 *
 * Prerender refresh 2026-08-05 (PR #777): the last 38 TRANSLATED briefs — the
 * es/lg/pt/sw/uk/ar rows the old translate_sermon bug had emptied — so every
 * sermon fixture in the library now carries one. Backend-only again, and the
 * chunk-hash warning above proved itself: the hash had already moved (other
 * merges) while all five localized shelves still served bare titles. The
 * localized pages are the whole point of this rebuild — `/es/sermons/` and
 * friends bake their brief at build time, so without it the translations exist
 * only in the api.
 *
 * Prerender refresh 2026-08-05 (queue jobs #635/#636/#637/#653/#654/#655/#766/
 * #767): eight more Arabic sermons take that language from four to twelve —
 * Spurgeon's المسيح كريم عند المؤمنين and النعمة المجّانيّة, Moody's المسيح
 * الكلّ في الكلّ, مواعيد المسيح الثمانية: «أُريد» and اللصّ المحتضر, Hudson
 * Taylor's الشدّة المباركة, A. B. Simpson's هو نفسه, and قوّة السكون. Each
 * carries a translated "In brief", and per the note above the brief TEXT is
 * what to check in the served HTML — not the chunk hash.
 *
 * Prerender refresh 2026-08-09 (queue job #425, PR #917): Spurgeon's "Free
 * Grace" landed in Swahili as Neema ya Bure. Re-crawl /sw/sermons so the card
 * and its /sw/sermons/free-grace page bake the translated title and the "In
 * brief" summary. #917 was backend-only (one fixture file), so per the #741
 * note above Render would otherwise SKIP the web build and the sw shelf would
 * keep serving the English title while the api served the Swahili one. Note
 * /lg/sermons already carries a Free Grace (job #249, Ekisa eky'Obwereere) —
 * this is the Swahili edition, a different file entirely.
 */
export const load: PageLoad = async () => {
	const { items, loadError } = await loadShelf(listSermons(getLang()));
	return { sermons: items, loadError };
};
