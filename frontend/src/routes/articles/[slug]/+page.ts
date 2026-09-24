import { getArticle, listArticles } from '$lib/library-public';
import { getLang } from '$lib/lang.svelte';
import { ApiError } from '$lib/api';
import { error } from '@sveltejs/kit';
import type { EntryGenerator, PageLoad } from './$types';

// Trailing-slash canonical -> prerenders to articles/<slug>/index.html, which
// the static host serves as a directory index (see books/[slug] for the note).
export const trailingSlash = 'always';

// This route serves TWO kinds of page under one segment: an article
// (`/articles/how-to-pray-so-god-answers/`) and a topic-filtered shelf
// (`/articles/prayer/`). They can't collide — article slugs are long,
// title-derived phrases; a topic slug is a short curated Topic slug — and
// load() resolves deterministically: it tries the article first, and a topic
// slug simply 404s there and falls through. entries() prerenders both sets, so
// each topic shelf is a real built page with its own H1 and canonical rather
// than the client-side `?topic=` filter it replaces.
export const entries: EntryGenerator = async () => {
	try {
		const articles = await listArticles('en');
		const slugs = new Set<string>();
		for (const a of articles) {
			slugs.add(a.slug);
			for (const tc of a.topics ?? []) slugs.add(tc.slug);
		}
		return [...slugs].map((slug) => ({ slug }));
	} catch {
		// The endpoint may lag on a fresh deploy (api + web build together), so
		// degrade to no article/topic pages rather than fail the whole build; a
		// later rebuild picks them up once the API is serving them.
		return [];
	}
};

export const load: PageLoad = async ({ params, fetch }) => {
	// Common path: a real article. getLang() (not a hardcoded 'en') is
	// intentional — the detail page is already built translation-ready
	// (self-referential canonical + hreflang from available_languages) while the
	// index, entries() and sitemap stay English-only for now. getArticle falls
	// back to English on a 404, so a localized URL degrades to the English
	// original rather than 404ing.
	try {
		const article = await getArticle(params.slug, getLang(), fetch);
		return { kind: 'article' as const, article };
	} catch (e) {
		// ONLY a 404 means "not an article, maybe a topic". Any other failure (a
		// 5xx, a malformed payload) propagates — a transient API error must not be
		// silently reinterpreted as a topic shelf or a 404.
		if (!(e instanceof ApiError) || e.status !== 404) throw e;
	}

	// Not an article — is the slug a published topic that tags ≥1 article? The
	// index list carries each article's topic chips, so its union is exactly the
	// set entries() prerenders and the only set that can render a non-empty shelf.
	const articles = await listArticles('en', fetch);
	const tab = articles.flatMap((a) => a.topics ?? []).find((tc) => tc.slug === params.slug);
	if (!tab) throw error(404, 'Not found');
	return { kind: 'topic' as const, topicSlug: tab.slug, topicTitle: tab.title, articles };
};
