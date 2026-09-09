<script lang="ts">
	import type { ArticleSummary } from '$lib/library-public';
	import ArticleCard from '$lib/components/ArticleCard.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import { articleHasTopic } from '$lib/articleTopics';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;

	/**
	 * The topic-filter row + the article card list, shared by the /articles index
	 * and each /articles/<topic>/ shelf.
	 *
	 * The chips are real links, not a client-side filter: each topic view is its
	 * own crawlable URL (`/articles/<slug>/`) with its own H1 and canonical, which
	 * is the whole point of the clean path — a `?topic=` query gave one indexable
	 * page for the lot. "All" is the bare index. Articles are English-only, so the
	 * hrefs are plain (no locale prefix), matching the index's English literals.
	 */
	let {
		articles,
		activeTopic = ''
	}: {
		/** The full shelf — tabs and their counts are derived from it. */
		articles: ArticleSummary[];
		/** The topic slug this view is filtered to; '' is the unfiltered index. */
		activeTopic?: string;
	} = $props();

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
		activeTopic ? articles.filter((a) => articleHasTopic(a, activeTopic)) : articles
	);
</script>

{#if topicTabs.length > 1}
	<nav class="filter-row mb-6" aria-label={t('articles.filterByTopic')}>
		<a class="chip" class:active={activeTopic === ''} aria-current={activeTopic === '' ? 'page' : undefined} href="/articles/">
			{t('search.filterAll')} <span class="count">{articles.length}</span>
		</a>
		{#each topicTabs as tab (tab.slug)}
			<a
				class="chip"
				class:active={activeTopic === tab.slug}
				aria-current={activeTopic === tab.slug ? 'page' : undefined}
				href="/articles/{tab.slug}/"
			>
				{tab.title} <span class="count">{tab.count}</span>
			</a>
		{/each}
	</nav>
{/if}

{#if shown.length}
	<div class="flex flex-col gap-3">
		{#each shown as a (a.slug)}
			<ArticleCard article={a} />
		{/each}
	</div>
{:else}
	<!-- Reachable only via a stale/hand-edited topic slug (a live chip always has
	     ≥1 article) — show a way back rather than a blank page. -->
	<EmptyState message={t('articles.emptyTopic')} />
{/if}
