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
 */
export const load: PageLoad = async () => {
	try {
		return { books: await listBooks(getLang()), loadError: false };
	} catch {
		return { books: [] as BookSummary[], loadError: true };
	}
};
