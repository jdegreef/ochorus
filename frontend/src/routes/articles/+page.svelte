<script lang="ts">
	import type { ArticleSummary } from '$lib/library-public';
	import ArticleCard from '$lib/components/ArticleCard.svelte';
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumb, hreflangFor } from '$lib/seo';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import { i18n } from '$lib/i18n.svelte';

	// English literals, as on /quotes and /scripture: this index is not localized
	// because what it lists is not (articles are English-only for now).
	let { data } = $props();
	const articles = $derived<ArticleSummary[]>(data.articles);
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;

	const path = '/articles/';
	const canonical = `${SITE_URL}${path}`;
	const hreflang = hreflangFor(path, ['en']);

	const title = 'Articles on prayer, faith & the Christian life — Ochorus';
	const description =
		'Short, plain-spoken readings on prayer, faith, grace and the life with God — ' +
		'each one pointing you to a classic Christian book, sermon or life worth reading in full, ' +
		'free.';

	const crumbs = [
		{ name: 'Home', href: '/' },
		{ name: 'Articles', href: path }
	];
	const crumbsLd = $derived(jsonLd(breadcrumb(crumbs.map((c) => ({ name: c.name, url: c.href })))));
	// A CollectionPage listing each article, so the set reads as one entity to a
	// crawler rather than a handful of unrelated URLs.
	const listLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: 'Articles',
			description,
			url: canonical,
			hasPart: articles.map((a) => ({
				'@type': 'Article',
				headline: a.h1,
				url: `${SITE_URL}/articles/${a.slug}/`
			}))
		})
	);
</script>

<Seo {title} {description} {canonical} {hreflang} structuredData={[crumbsLd, listLd]} />

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<PageHeader
		title="Articles"
		tagline="Short readings on prayer, faith and the life with God — each one written to send you on to a classic worth reading in full."
	/>

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if articles.length}
		<div class="article-list">
			{#each articles as a (a.slug)}
				<ArticleCard article={a} />
			{/each}
		</div>
	{:else}
		<EmptyState message="No articles yet — check back soon." />
	{/if}
</div>

<style>
	.article-list {
		display: grid;
		gap: 0.75rem;
		max-width: 44rem;
	}
</style>
