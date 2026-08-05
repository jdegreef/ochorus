import { listBooks, type BookSummary } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

/**
 * Await the shelf so the page prerenders with real content (and its JSON-LD),
 * folding a fetch failure into `{ loadError: true }` so a client-side navigation
 * to a down API shows a retry panel instead of the error route.
 *
 * Prerender refresh 2026-07-15: force an ochorus-web rebuild after the api went
 * live with the 4 new Spanish (es) books, so the localized /es/books index and
 * the /es/books/<slug> pages re-crawl and bake with the new titles.
 *
 * Prerender refresh 2026-07-15 (lg/sw): same again after the Luganda + Swahili
 * translations went live, so /lg/books and /sw/books (and their /<slug> pages)
 * re-crawl and bake with the new titles.
 *
 * Prerender refresh 2026-07-15 (classic authors): force an ochorus-web rebuild
 * after the api went live with 11 new public-domain works (Bunyan, Watson,
 * Baxter, Edwards, Whitefield, Wesley), so the /books index, the new
 * /books/<slug> and /authors/<slug> pages, and the sitemap re-crawl and bake.
 *
 * Prerender refresh 2026-07-17 (queue job #169): same again after the Luganda
 * edition of Clothed with Strength and Dignity went live, so /lg/books and
 * its /books/<slug> pages re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-17 (queue job #170): same again after the Luganda
 * edition of The Key in My Hand (Ekisumuluzo Ekiri mu Mukono Gwange, PR #174)
 * went live, so the /lg/books pages re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-17 (queue job #179): same again after the Luganda
 * edition of Godliness (Okutya Katonda, PR #184) went live, so the /lg/books
 * pages re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-19 (queue job #199): same again after the Spanish
 * edition of Prayer – The Pulse of Life (Oración – El Pulso de la Vida, PR
 * #226) went live, so the /es/books index and its /books/<slug> pages re-crawl
 * and bake with the new title.
 *
 * Prerender refresh 2026-07-19 (queue job #200): same again after the Spanish
 * edition of Clothed with Strength and Dignity (Revestida de fuerza y dignidad,
 * PR #228) went live, so the /es/books index and its /books/<slug> pages
 * re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-19 (queue job #201): same again after the Spanish
 * edition of Godliness (La piedad, PR #230) by Catherine Booth went live, so
 * the /es/books index and its /books/<slug> pages re-crawl and bake with the
 * new title.
 *
 * Prerender refresh 2026-07-20 (queue job #202): same again after the Spanish
 * edition of The Key in My Hand (La llave en mi mano, PR #235) by Gareth Evans
 * went live, so the /es/books index and its /books/<slug> pages re-crawl and
 * bake with the new title.
 *
 * Prerender refresh 2026-07-20 (queue job #246): same again after the Luganda
 * edition of Humility (Obwetoowaze, PR #255) by Andrew Murray went live, so the
 * /lg/books index and its /books/<slug> pages re-crawl and bake with the new
 * title.
 *
 * Prerender refresh 2026-07-20 (queue job #247): same again after the Luganda
 * edition of Talks to the Farmer (Ebigambo eri Omulimi, PR #262) by C. H.
 * Spurgeon went live, so the /lg/books index and its /books/<slug> pages
 * re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-20 (queue job #248): same again after the Luganda
 * edition of The Way to God (Ekkubo Erituusa eri Katonda, PR #264) by D. L.
 * Moody went live, so the /lg/books index and its /books/<slug> pages re-crawl
 * and bake with the new title.
 *
 * Prerender refresh 2026-07-21 (queue job #273): same again after the Luganda
 * edition of The God of All Comfort (Katonda ow'Okubudaabuda Kwonna, PR #295)
 * by Hannah Whitall Smith went live, so the /lg/books index and its
 * /books/<slug> pages re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-21 (queue job #274): same again after the Luganda
 * edition of Stepping Stones (Amayinja g'Okulinnyirako, PR #298) by Gareth
 * Evans went live, so the /lg/books index and its /books/<slug> pages re-crawl
 * and bake with the new title.
 *
 * Prerender refresh 2026-07-21 (queue job #275): same again after the Luganda
 * edition of Prevailing Prayer (Okusaba Okuwangula, PR #306) by D. L. Moody
 * went live, so the /lg/books index and its /books/<slug> pages re-crawl and
 * bake with the new title.
 *
 * Prerender refresh 2026-07-21 (queue job #276): same again after the Luganda
 * edition of All of Grace (Byonna Bya Kisa, PR #311) by C. H. Spurgeon went
 * live, so the /lg/books index and its /books/<slug> pages re-crawl and bake
 * with the new title.
 *
 * Prerender refresh 2026-07-21 (queue job #278): same again after the Swahili
 * edition of Clothed with Strength and Dignity (Amevaa Nguvu na Heshima,
 * PR #314) went live, so the /sw/books index and its /books/<slug> pages
 * re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-22 (queue job #279): same again after the Swahili
 * edition of The Key in My Hand (Ufunguo Ulio Mkononi Mwangu, PR #316) by
 * Gareth Evans went live, so the /sw/books index and its /books/<slug> pages
 * re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-22 (queue job #280): same again after the Swahili
 * edition of Prayer – The Pulse of Life (Maombi – Mapigo ya Uhai, PR #322) by
 * Hannah Buyinza went live, so the /sw/books index and its /books/<slug> pages
 * re-crawl and bake with the new title.
 *
 * Prerender refresh 2026-07-22 (queue job #281): same again after the Swahili
 * edition of Godliness (Utauwa, PR #332) by Catherine Booth went live, so the
 * /sw/books index and its /books/<slug> pages re-crawl and bake with the new
 * title.
 *
 * Prerender refresh 2026-07-22 (School of Prayer source books): after the
 * Luganda + Swahili editions of Lord, Teach Us To Pray (Mukama, Tuyigirize
 * Okusaba / Bwana, Tufundishe Kuomba) and the Swahili Prevailing Prayer
 * (Maombi Yenye Kushinda) went live (PR #351), so the /lg/books and /sw/books
 * indexes and their /books/<slug> pages re-crawl and bake with the new titles.
 *
 * Prerender refresh 2026-07-22 (Holy Spirit book in es/lg/sw): after the
 * Spanish, Luganda and Swahili editions of Torrey's The Person and Work of the
 * Holy Spirit (La Persona y la Obra del Espíritu Santo / Omuntu n'Omulimu
 * gw'Omwoyo Omutukuvu / Nafsi na Kazi ya Roho Mtakatifu, PR #365) went live, so
 * the /es|/lg|/sw books indexes and their /books/<slug> pages re-crawl and bake.
 *
 * Prerender refresh 2026-07-29 (queue job #476): the first Portuguese book —
 * The Inner Chamber (A Câmara Interior), 36 ch — ships (PR #522). The /pt books
 * index and /pt/books/the-inner-chamber with its chapter pages re-crawl and
 * bake the translation.
 *
 * Prerender refresh 2026-07-29 (queue jobs #484/#485/#491/#506/#507): the rest
 * of the Portuguese library — Vestida de Força e Dignidade, A Chave na Minha
 * Mão, O batismo com o Espírito Santo, Piedade and O Próprio Jesus, 53 chapters
 * in all — ships (PR #534), so the /pt books index and each /pt/books/<slug>
 * with its chapter pages re-crawl and bake the translations.
 *
 * Prerender refresh 2026-07-29 (salvaged from #525): Senhor, Ensina-nos a Orar
 * (Lord, Teach Us To Pray), 4 ch — the one book #525 still had that main
 * lacked — ships (PR #558), so the /pt books index and
 * /pt/books/lord-teach-us-to-pray-2 with its chapter pages re-crawl and bake
 * the translation.
 *
 * Prerender refresh 2026-07-30 (queue jobs #604/#605): the first Spanish
 * editions of Spurgeon's Todo por Gracia (All of Grace, 20 ch) and Moody's
 * La oración que prevalece (Prevailing Prayer, 11 ch) ship, so the /es books
 * index and /es/books/all-of-grace and /es/books/prevailing-prayer with their
 * chapter pages re-crawl and bake the translations.
 *
 * Prerender refresh 2026-07-31 (queue jobs #625/#627/#628): the FIRST ARABIC
 * BOOKS in the library — Torrey's المعمودية بالروح القدس (Baptism with the Holy
 * Spirit, 5 ch), لابسة العزّ والبهاء (Clothed with Strength and Dignity, 15 ch)
 * and Gareth Evans's المفتاح الذي في يدي (The Key in My Hand, 15 ch), 35
 * chapters in all. Arabic is RTL: the chapter bodies carry no dir/lang of their
 * own, so the /ar books index and each /ar/books/<slug> with its chapter pages
 * render under the container's dir="auto" (see readerDirection.test.ts) and
 * re-crawl to bake the translated titles and text.
 *
 * Prerender refresh 2026-07-31 (queue jobs #670/#671): the FIRST UKRAINIAN
 * BOOKS — Зодягнена в силу й гідність (Clothed with Strength and Dignity,
 * 15 ch) and Andrew Murray's Сам Ісус (Jesus Himself, 2 ch), 17 chapters in
 * all. Ukrainian is LTR, so no direction handling is needed; the /uk books
 * index and each /uk/books/<slug> with its chapter pages re-crawl and bake the
 * translations. Note uk seeds as status=draft, so these only reach readers once
 * the language is launched from the admin.
 *
 * Prerender refresh 2026-08-01 (queue job #669): Andrew Murray's Внутрішня
 * кімната (The Inner Chamber, 36 ch) completes the Ukrainian book queue —
 * three uk books, 53 chapters in all. The /uk books index and
 * /uk/books/the-inner-chamber with its chapter pages re-crawl and bake.
 *
 * Prerender refresh 2026-08-01 (queue job #629): the Arabic edition of Andrew
 * Murray's المخدع (The Inner Chamber, 36 ch) — Arabic's fourth book. Arabic is
 * RTL: the chapter bodies carry no dir/lang of their own, so the /ar books
 * index and /ar/books/the-inner-chamber render under the container's
 * dir="auto" (see readerDirection.test.ts) and re-crawl to bake the
 * translation.
 *
 * Prerender refresh 2026-08-04 (queue job #626): Gareth Evans's غَدي في يديه
 * (He Holds My Tomorrows, 18 ch) — Arabic's fifth book, and its first modern
 * devotional rather than a classic. Same RTL handling as #629: the chapter
 * bodies carry no dir/lang of their own, so /ar/books and
 * /ar/books/he-holds-my-tomorrows render under the container's dir="auto"
 * (see readerDirection.test.ts) and re-crawl to bake the translation.
 *
 * Prerender refresh 2026-08-04 (the plan #650 unblock): R. A. Torrey's أقنوم
 * الروح القدس وعمله (The Person and Work of the Holy Spirit, 22 ch) — Arabic's
 * sixth book and its longest yet. Same RTL handling. This one also makes the
 * reading plan power-from-on-high render in Arabic, so /ar/plans changes too:
 * seed_plans creates a plan only in a language where EVERY source book exists,
 * and its other source (المعمودية بالروح القدس) has been Arabic since #625.
 *
 * Prerender refresh 2026-08-05 (queue jobs #754, #755, #729): three books at
 * once — Andrew Murray's يا ربّ، علّمنا أن نصلّي (4 ch), D. L. Moody's الصلاة
 * الغالبة (11 ch) and Hannah Buyinza's الصلاة — نبض الحياة (12 ch) — taking
 * Arabic from six books to nine. Same RTL handling as #629. They ship together
 * on purpose: they are the three sources of the reading plan A School of Prayer
 * (#630), and by the same EVERY-source-book rule as #650 the plan cannot
 * render in Arabic until the last of them lands, so /ar/plans changes too.
 *
 * Prerender refresh 2026-08-05 (queue job #417): Gareth Evans's Mawe ya
 * Kukanyagia (Stepping Stones, 39 ch) — Swahili's thirteenth book and its
 * longest, and the third of this author's in Swahili alongside Anazishika
 * Kesho Zangu and Ufunguo Ulio Mkononi Mwangu. The /sw books index and
 * /sw/books/stepping-stones-2 with its chapter pages re-crawl and bake.
 */
export const load: PageLoad = async () => {
	try {
		return { books: await listBooks(getLang()), loadError: false };
	} catch {
		return { books: [] as BookSummary[], loadError: true };
	}
};
