<script lang="ts">
	import type { ArticleSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, hreflangFor } from '$lib/seo';
	import PageHeader from '$lib/components/PageHeader.svelte';
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
	<PageHeader title={seo.h1} tagline={seo.blurb} />
	<ArticleShelf {articles} activeTopic={slug} />
</div>
