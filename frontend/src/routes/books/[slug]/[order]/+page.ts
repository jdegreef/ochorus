import { building } from '$app/environment';
import { getChapter, listBooks, MODERN_EDITION } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import { orNotFound } from '$lib/loadHelpers';
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
export const prerender = true;
export const trailingSlash = 'always';

// One entry per English chapter; the localized copies are discovered by the
// crawler through each localized book page's table of contents (the same
// mechanism that prerenders /es /sw /lg book pages today).
export const entries: EntryGenerator = async () => {
	const books = await listBooks('en');
	return books.flatMap((b) =>
		Array.from({ length: b.chapter_count }, (_, i) => ({
			slug: b.slug,
			order: String(i + 1)
		}))
	);
};

export const load: PageLoad = async ({ params, url }) => {
	// ?edition=modern reads the Modern English edition (en-modern) instead of the
	// locale copy. Query params don't exist at prerender time (touching
	// url.searchParams here would fail the build), so the static HTML is always
	// the standard edition; a direct visit with ?edition=modern is reconciled
	// client-side by the page (it re-runs this load, where `building` is false).
	const modern = !building && url.searchParams.get('edition') === 'modern';
	const chapter = await orNotFound(() =>
		getChapter(params.slug, Number(params.order), modern ? MODERN_EDITION : getLang())
	);
	return { chapter, slug: params.slug, edition: modern ? 'modern' : null };
};
