import { redirect } from '@sveltejs/kit';
import { building } from '$app/environment';
import { getChapterWithLang, listBooks } from '$lib/library-public';
import { getLang } from '$lib/lang.svelte';
import { localizeHref } from '$lib/href';
import { modernChapterPath } from '$lib/reading-schema';
import { chapterEntries, orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

// Prerendered like the book pages: the chapter text is the site's core
// content, and as a client-only SPA shell it was invisible to search engines
// and link previews. The reader's interactivity (marks, listen, progress) is
// all client-side on top of the static text. Trailing slash so each chapter
// lands as <order>/index.html, which the static host serves reliably.
// Prerender refresh 2026-08-04: 244 chapter rows across 8 books and 7
// languages lost a leading paragraph — the editorial chapter summaries the
// ochorus.com import prefixed to the author's own prose. The chapter text is
// baked into these prerendered pages, so the api serving the corrected body is
// not enough on its own; the site has to rebuild or readers keep seeing the
// summary. That is the whole job of this comment.
// Prerender refresh 2026-08-04 (headings): 175 chapter rows across 11 books
// gained <h2> section headings the PDF import had fused into the prose or left
// as stubby paragraphs. This changes the shape of the page, not just a word, so
// the static build has to run for readers to see it.
// Prerender refresh 2026-08-04 (humility-2 ch09, en + lg): a source defect had
// the Syrophenician mother accepting "the name of God" where the author wrote
// "dog" — the illustration argued its own opposite. Same reason as above: the
// corrected body has to be re-baked, not just served.
// Prerender refresh 2026-08-05 (humility-2 ar): a WHOLE new edition, so these
// pages do not exist yet rather than being stale — the entry generators ask the
// api for the book list at build time, which means the web build has to run
// AFTER the api has seeded the Arabic rows, not alongside it.
// Prerender refresh 2026-08-05 (queue jobs #754, #755, #729): the three source
// books of the reading plan A School of Prayer land in Arabic together — يا ربّ،
// علّمنا أن نصلّي (4 ch), الصلاة الغالبة (11 ch) and الصلاة — نبض الحياة (12 ch),
// 27 chapters in all. Arabic is RTL: the chapter bodies carry no dir/lang of
// their own, so each /ar/books/<slug>/<order> renders under the container's
// dir="auto" (see readerDirection.test.ts) and re-crawls to bake the text.
// Prerender refresh 2026-08-05 (queue job #417): Mawe ya Kukanyagia (Stepping
// Stones, 39 ch) is the longest book Swahili has, so each
// /sw/books/stepping-stones-2/<order> is a new page the crawler has to bake.
// Prerender refresh 2026-08-05 (queue job #418): Unyenyekevu (Humility, 12 ch)
// adds twelve more /sw chapter pages that do not exist yet.
export const prerender = true;
export const trailingSlash = 'always';

// One entry per English chapter; the localized copies are discovered by the
// crawler through each localized book page's table of contents (the same
// mechanism that prerenders /es /sw /lg book pages today).
export const entries: EntryGenerator = async () => chapterEntries(await listBooks('en'));

export const load: PageLoad = async ({ params, url, fetch }) => {
	// ?edition=modern is the Modern English edition's OLD address (bookmarks,
	// shared links, saved marks): send it to the edition's own route, keeping the
	// rest of the query (?p=, plan context). Before any fetch — the modern route
	// sends a work with no modern edition back here. Never at build time: query
	// params don't exist then (touching url.searchParams would fail the build).
	if (!building && url.searchParams.get('edition') === 'modern') {
		const qs = new URLSearchParams(url.search);
		qs.delete('edition');
		const q = qs.toString();
		redirect(307, localizeHref(`${modernChapterPath(params.slug, Number(params.order))}${q ? `?${q}` : ''}`));
	}
	// The language the body is actually IN — needed for the prose's `lang`
	// attribute, since the Chapter payload carries none of its own and without it
	// the browser hyphenates (and a screen reader pronounces) against the UI
	// locale, which is routinely not the language on the page.
	//
	// It must be the RESOLVED language, not the requested one: getChapter falls
	// back to English on a 404, so a book with no Arabic copy read under /ar
	// returns English prose. Labelling that `lang="ar"` is worse than saying
	// nothing — a wrong value actively misleads where a missing one abstains.
	const { data: chapter, language } = await orNotFound(() =>
		getChapterWithLang(params.slug, Number(params.order), getLang(), fetch)
	);
	// The shared reader component's prop shape: the modern route sets 'modern'.
	return { chapter, slug: params.slug, language, edition: null as 'modern' | null };
};
