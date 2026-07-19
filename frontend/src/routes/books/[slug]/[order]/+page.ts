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
