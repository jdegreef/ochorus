<script lang="ts">
	import type { ArticleSummary } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { readingTime } from '$lib/reading';

	let { article }: { article: ArticleSummary } = $props();
</script>

<!-- A row card (border-tint hover, no lift — see page-design D3). The title is
     the card's link, stretched over the whole card via ::after so the card is
     clickable; the topic chips are real links that sit above the overlay
     (z-index) so they navigate to their topic pages, not the article. -->
<article class="article-card">
	<h2 class="text-h3">
		<a class="card-link" href={localizeHref(`/articles/${article.slug}/`)}>{article.h1}</a>
	</h2>
	{#if article.description}
		<p class="mt-1 text-body text-muted">{article.description}</p>
	{/if}
	<div class="meta">
		<span class="read-time">{readingTime(article.word_count)}</span>
		{#each article.topics as topic (topic.slug)}
			<a class="chip topic-chip" href={localizeHref(`/topics/${topic.slug}`)}>{topic.title}</a>
		{/each}
	</div>
</article>

<style>
	.article-card {
		position: relative;
		padding: 1.1rem 1.25rem;
		border: 1px solid var(--color-border);
		border-radius: 0.75rem;
		background: var(--color-surface);
		transition: border-color var(--duration-fast) ease;
	}
	.article-card:hover {
		border-color: var(--color-accent);
	}
	.article-card h2 {
		color: var(--color-text);
	}
	.card-link {
		color: inherit;
		text-decoration: none;
	}
	/* Stretch the title link over the whole card so the card is one click
	   target, while real links inside (topic chips) stay above it. */
	.card-link::after {
		content: '';
		position: absolute;
		inset: 0;
	}
	.meta {
		margin-top: 0.7rem;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem;
	}
	.read-time {
		font-family: var(--font-sans);
		font-size: var(--fs-small);
		color: var(--color-muted);
	}
	.topic-chip {
		position: relative;
		z-index: 1;
		text-decoration: none;
	}
</style>
