<script lang="ts">
	import type { ArticleSummary } from '$lib/library-public';
	import ArticleCard from '$lib/components/ArticleCard.svelte';
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumbLd, hreflangFor } from '$lib/seo';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { page } from '$app/stores';
	import { urlFilters } from '$lib/urlFilters.svelte';

	// English literals, as on /quotes and /scripture: this index is not localized
	// because what it lists is not (articles are English-only for now).
	let { data } = $props();
	const articles = $derived<ArticleSummary[]>(data.articles);
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;

	// Topic-filter chips, kept in the URL like the books shelf (shareable, and
	// honouring Back/Forward) — the same `urlFilters` engine, not a private fork.
	// A prerendered page must not read the query string during setup; urlFilters
	// handles that, so the bare `/articles/` still serves every card.
	const filters = urlFilters({
		defaults: { topic: '' },
		url: () => $page.url
	});

	// Distinct topics present on the shelf, alphabetical, each with a count for
	// its chip badge. `?? []` guards a lagging API that predates the `topics`
	// field (version skew).
	type TopicTab = { slug: string; title: string; count: number };
	const topicTabs = $derived.by<TopicTab[]>(() => {
		const bySlug = new Map<string, TopicTab>();
		for (const a of articles) {
			for (const tc of a.topics ?? []) {
				const seen = bySlug.get(tc.slug);
				if (seen) seen.count += 1;
				else bySlug.set(tc.slug, { slug: tc.slug, title: tc.title, count: 1 });
			}
		}
		return [...bySlug.values()].sort((x, y) => x.title.localeCompare(y.title));
	});

	const shown = $derived(
		filters.values.topic
			? articles.filter((a) => (a.topics ?? []).some((tc) => tc.slug === filters.values.topic))
			: articles
	);

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
	const crumbsLd = breadcrumbLd(crumbs);
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
	<!-- No visible breadcrumb: a top-level hub's only trail is Home > <this>
	     — Home is already the logo, <this> restates the H1 below, so it
	     carries nothing. The BreadcrumbList JSON-LD stays in the head; the
	     page's position is true even when we don't draw it. -->
	<PageHeader
		title="Articles"
		tagline="Short readings on prayer, faith and the life with God — each one written to send you on to a classic worth reading in full."
	/>

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if articles.length}
		{#if topicTabs.length > 1}
			<div class="filter-row mb-6" role="group" aria-label="Filter articles by topic">
				<button
					type="button"
					class="chip"
					class:active={filters.values.topic === ''}
					aria-pressed={filters.values.topic === ''}
					onclick={() => (filters.values.topic = '')}
				>
					All <span class="count">{articles.length}</span>
				</button>
				{#each topicTabs as tab (tab.slug)}
					<button
						type="button"
						class="chip"
						class:active={filters.values.topic === tab.slug}
						aria-pressed={filters.values.topic === tab.slug}
						onclick={() =>
							(filters.values.topic = filters.values.topic === tab.slug ? '' : tab.slug)}
					>
						{tab.title} <span class="count">{tab.count}</span>
					</button>
				{/each}
			</div>
		{/if}

		{#if shown.length}
			<div class="article-list">
				{#each shown as a (a.slug)}
					<ArticleCard article={a} />
				{/each}
			</div>
		{:else}
			<!-- Reachable only via a stale/hand-edited ?topic= (a live chip always
			     has ≥1 article) — show a way back rather than a blank page. -->
			<EmptyState message="No articles under that topic." />
		{/if}
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
