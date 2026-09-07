<script lang="ts">
	import ArticleDetail from '$lib/components/ArticleDetail.svelte';
	import ArticleTopicShelf from '$lib/components/ArticleTopicShelf.svelte';

	// One route, two pages: an article reader or a topic-filtered shelf. The load
	// function tags which (data.kind); each branch is a self-contained component
	// so neither runs the other's article-/topic-specific setup. See +page.ts.
	let { data } = $props();
</script>

{#if data.kind === 'topic'}
	<ArticleTopicShelf slug={data.topicSlug} title={data.topicTitle} articles={data.articles} />
{:else}
	<ArticleDetail article={data.article} />
{/if}
