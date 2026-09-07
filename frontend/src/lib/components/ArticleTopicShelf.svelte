<script lang="ts">
	import type { ArticleSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, hreflangFor } from '$lib/seo';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import ArticleShelf from '$lib/components/ArticleShelf.svelte';
	import { articleTopicSeo, articleHasTopic, articleCollectionLd } from '$lib/articleTopics';

	// The /articles/<topic>/ shelf — the article index filtered to one topic,
	// with its own keyword-led H1 and canonical so it reads as a page about the
	// subject rather than a duplicate of /articles. Its sibling on this route is
	// the article reader (ArticleDetail); the [slug]/+page.svelte switch picks
	// one from data.kind. English-only like the index, so plain (unlocalized)
	// hrefs and an en-only hreflang.
	let {
		slug,
		title,
		articles
	}: {
		/** The topic's slug (the path segment). */
		slug: string;
		/** The topic's localized chip title, for the crumb and the SEO fallback. */
		title: string;
		/** The full article shelf — the chips and the filtered list derive from it. */
		articles: ArticleSummary[];
	} = $props();

	const seo = $derived(articleTopicSeo(slug, title));
	const shown = $derived(articles.filter((a) => articleHasTopic(a, slug)));

	const path = $derived(`/articles/${slug}/`);
	const canonical = $derived(`${SITE_URL}${path}`);
	const hreflang = $derived(hreflangFor(path, ['en']));

	const crumbs = $derived([
		{ name: 'Home', href: '/' },
		{ name: 'Articles', href: '/articles/' },
		{ name: title, href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
	// A CollectionPage scoped to this topic's articles — the topic view's twin of
	// the index's list, so each shelf reads as one entity to a crawler.
	const listLd = $derived(articleCollectionLd(seo.h1, seo.blurb, canonical, shown));
</script>

<Seo
	title="{seo.h1} — Ochorus"
	description={seo.blurb}
	{canonical}
	{hreflang}
	structuredData={[crumbsLd, listLd]}
/>

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />
	<!-- Not <PageHeader>: its tagline is hard-capped at max-w-2xl (shared across
	     Books/Topics/…), and this shelf's standfirst is its own 80–130-word intro
	     (seo.intro) with a reading measure tuned for a paragraph, not a one-liner.
	     The H1 mirrors PageHeader's classes so the two headers still match.
	     seo.blurb stays the meta description only (see <Seo> above). -->
	<header class="mb-8">
		<h1 class="text-h1 mb-3">{seo.h1}</h1>
		<p class="article-topic-intro text-body text-muted">{seo.intro}</p>
	</header>
	<ArticleShelf {articles} activeTopic={slug} />
</div>

<style>
	/* The standfirst is an 80–130-word paragraph, so it keeps a reading measure
	   (~75 characters) rather than spanning the full content column — long lines
	   at page-col width are hard to track back to the next line. It sits a touch
	   wider than PageHeader's max-w-2xl (42rem) tagline, matching its longer copy. */
	.article-topic-intro {
		max-inline-size: 46rem;
		text-wrap: pretty;
	}
</style>
