<script lang="ts">
	import type { ArticleSummary } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { readingTime } from '$lib/reading';

	// `heading`: the card title's level. h2 where the cards ARE the page's
	// sections (the Articles index); h3 where they sit under a section heading
	// of their own (a topic's "Articles"), so the outline doesn't read as
	// seventeen top-level sections.
	let { article, heading = 'h2' }: { article: ArticleSummary; heading?: 'h2' | 'h3' } =
		$props();
</script>

<!-- A row card (border-tint hover, no lift — see page-design D3). The whole card
     is one link; the taxonomy lives in the index's topic-filter tabs, so the
     card carries only the title, standfirst and reading time. -->
<a
	class="article-card card-tint border border-border bg-surface"
	href={localizeHref(`/articles/${article.slug}/`)}
>
	<svelte:element this={heading} class="card-title text-h3">{article.h1}</svelte:element>
	{#if article.description}
		<p class="mt-1 text-body text-muted">{article.description}</p>
	{/if}
	<span class="read-time">{readingTime(article.word_count)}</span>
</a>

<style>
	/* Row card. Padding, radius and link colours are scoped; the resting border
	   and ground ride on layered Tailwind utilities in the markup, and the hover
	   (border→accent, ground→surface-2, no lift) on the shared .card-tint — so
	   nothing ties this scoped rule and the hover always wins, exactly like
	   .sermon-card (page-design D3/H1). */
	.article-card {
		display: block;
		padding: 1.1rem 1.25rem;
		border-radius: 0.75rem;
		text-decoration: none;
		color: inherit;
	}
	.article-card :global(.card-title) {
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
