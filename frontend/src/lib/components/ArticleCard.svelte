<script lang="ts">
	import type { ArticleSummary } from '$lib/library-public';
	import { localizeHref } from '$lib/href';

	let { article }: { article: ArticleSummary } = $props();
</script>

<a class="article-card" href={localizeHref(`/articles/${article.slug}/`)}>
	<h3 class="text-h3">{article.h1}</h3>
	{#if article.description}
		<p class="mt-1 text-body text-muted">{article.description}</p>
	{/if}
	<span class="read-more">Read →</span>
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
			border-color 0.15s ease,
			transform 0.15s ease;
	}
	.article-card:hover {
		border-color: var(--color-accent);
		transform: translateY(-1px);
	}
	.article-card h3 {
		color: var(--color-text);
	}
	.read-more {
		display: inline-block;
		margin-top: 0.6rem;
		font-family: var(--font-sans);
		font-weight: 600;
		color: var(--color-accent);
	}
</style>
