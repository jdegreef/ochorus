<script lang="ts">
	import type { ArticleSummary } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { readingTime } from '$lib/reading';

	let { article }: { article: ArticleSummary } = $props();
</script>

<!-- A row card (border-tint hover, no lift — see page-design D3). The whole card
     is one link; the taxonomy lives in the index's topic-filter tabs, so the
     card carries only the title, standfirst and reading time. -->
<a class="article-card" href={localizeHref(`/articles/${article.slug}/`)}>
	<h2 class="text-h3">{article.h1}</h2>
	{#if article.description}
		<p class="mt-1 text-body text-muted">{article.description}</p>
	{/if}
	<span class="read-time">{readingTime(article.word_count)}</span>
</a>

<style>
	.article-card {
		display: block;
		padding: 1.1rem 1.25rem;
		border: 1px solid var(--color-border);
		border-radius: 0.75rem;
		background: var(--color-surface);
		text-decoration: none;
		color: inherit;
		transition:
			border-color var(--duration-fast) ease,
			background var(--duration-fast) ease;
	}
	/* Row card, so it TINTS rather than lifts — the same border→accent +
	   bg→surface-2 as .sermon-card, so the two row families hover alike
	   (page-design H1). */
	.article-card:hover {
		border-color: var(--color-accent);
		background: var(--color-surface-2);
	}
	.article-card h2 {
		color: var(--color-text);
	}
	.read-time {
		display: block;
		margin-top: 0.7rem;
		font-family: var(--font-sans);
		font-size: var(--fs-small);
		color: var(--color-muted);
	}
</style>
