<script lang="ts">
	import { pagedSnapshot } from '$lib/paging.svelte';
	import ArticleDetail from '$lib/components/ArticleDetail.svelte';
	import ArticleTopicShelf from '$lib/components/ArticleTopicShelf.svelte';

	// One route, two pages: an article reader or a topic-filtered shelf. The load
	// function tags which (data.kind); each branch is a self-contained component
	// so neither runs the other's article-/topic-specific setup. See +page.ts.
	let { data } = $props();

	let shelf = $state<ArticleTopicShelf>();
	export const snapshot = pagedSnapshot(() => shelf?.pages);
</script>

{#if data.kind === 'topic'}
	<ArticleTopicShelf bind:this={shelf} slug={data.topicSlug} title={data.topicTitle} articles={data.articles} />
{:else}
	<ArticleDetail article={data.article} />
{/if}
