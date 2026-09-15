// Rebuild marker 2026-09-15b: #2412 added Isaac Watts's Divine Songs for
// Children + the new author isaac-watts. Same new-content prerender race —
// /books/divine-songs-for-children, /authors/isaac-watts and the updated
// /topics/for-young-readers shelf baked as shells. API confirmed live with
// all three; this touch forces one web build to prerender them.
// Rebuild marker 2026-09-15: #2401 added the retold Pilgrim's Progress
// (words of one syllable) + the for-young-readers shelf. The book's first
// deploy lost the prerender race — the web build enumerated /books before
// seed_books created the row, so /books/pilgrims-progress-words-of-one-syllable
// and /topics/for-young-readers baked as the 6 KB SPA shell. The API is
// confirmed live with both; this frontend touch forces one web build to
// prerender them.
// Rebuild marker 2026-09-02: #1320 added Augustine's Enchiridion (11 thematic
// chapters). The book's first deploy lost the prerender race — the web build
// enumerated /books before the API's seed_books created the row, so the page
// baked as the 5.7 KB SPA shell (empty <title>). The API is confirmed live with
// the book; this frontend touch forces one more web build to prerender it.
// Rebuild marker 2026-08-28: #1185 gave Purpose in Prayer's thirteen chapters
// editorial titles. Unlike the markers below, the page was NOT the SPA shell —
// it prerendered fine when the book shipped, but that build predates #1185, so
// the contents list is baked with the "Chapter 1" … "Chapter 13" fallback the
// reader shows for an untitled chapter. The api is confirmed live with the
// titles; the other three Bounds books and /authors/e-m-bounds are already
// correct, so this is the only stale page.
// Rebuild marker 2026-08-28: #1183 added The Bruised Reed. New books reach
// prod through `seed_books` in the api's release step, so the web build
// enumerated /books before the row existed and it served the SPA shell.
// Rebuild marker 2026-08-28: #1161 added On the Priesthood, The Life of Antony
// and On the Incarnation. New books reach prod through `seed_books` in the
// api's release step, so the web build enumerated /books before the rows
// existed and all three prerendered as the SPA shell — 5,688 bytes, no
// <title>, identical for every slug. The api is confirmed live with all
// three; this touch forces the build that actually prerenders them.
// Rebuild marker 2026-08-28: PR #1150 filled `CURATED_GROUND`, which is what
// makes `credit()` return an attribution line for the translated editions of
// the-inner-chamber and prayer-the-pulse-of-life. That PR touched frontend/
// (the paintings), so the web build DID run — in parallel with the api deploy,
// and the crawler's requests interleaved with the api's rollover: 6 of the 12
// translated pages prerendered against the OLD api, whose CURATED_GROUND was
// empty, and baked HTML with no credit. Scattered by language (es/lg/sw
// missing, ar/hi/pt/uk present) rather than a clean prefix, which is what a
// concurrent crawler against a rolling restart looks like. Readers saw the
// credit on hydration throughout; only the static HTML disagreed. This touch
// re-prerenders now the api is settled.

// Rebuild marker 2026-07-15: backend-only PR #121 backfilled descriptions for
// 16 books that imported without one; Render skips the web build for backend
// commits, so this touch forces a prerender against the migrated API data.
//
// Rebuild marker 2026-07-22: PR #355 self-hosted the covers. That PR DID touch
// frontend/ (the image files), so the web build ran — but it ran in parallel
// with the api's migration and baked the pre-migration cover_urls into
// og:image. The content-race, not a skipped build: verified 6 of 8 sampled
// book pages still advertising ochorus.com artwork while the API served
// /covers/. This touch re-prerenders now the migration is live.
import { getBook, listBooks } from '$lib/library-public';
import { getLang } from '$lib/lang.svelte';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

// Canonical URL carries a trailing slash so this page prerenders to
// books/<slug>/index.html — the static host (Render) serves a directory index
// only for the trailing-slash URL, so this is what keeps real book pages served
// as prerendered HTML while a missing slug falls through to the not-found page.
export const trailingSlash = 'always';

// Prerender one page per book — the slug list comes from the API at build time.
export const entries: EntryGenerator = async () => {
	const books = await listBooks('en');
	return books.map((b) => ({ slug: b.slug }));
};

export const load: PageLoad = async ({ params }) => {
	const book = await orNotFound(() => getBook(params.slug, getLang()));
	return { book };
};

// New public-domain books/sermons are prerendered per slug; a backend-only
// content merge skips the web build, so new /books/<slug> pages need this
// rebuild to exist as static HTML.

// Book detail is prerendered per locale; a backend-only content merge skips
// the web build, so a newly-translated book (e.g. the-inner-chamber in lg)
// needs this rebuild to prerender in that language.

// Refresh prerender: Finney + Brainerd (books, author bios, portrait) added
// via fixture; the web build prerendered before the API seeded them. 2026-07-13.
