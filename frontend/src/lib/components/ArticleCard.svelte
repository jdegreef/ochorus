<script lang="ts">
	import type { ArticleSummary } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { readingTime } from '$lib/reading';
	import { isGuide } from '$lib/articleIndex';
	import { i18n } from '$lib/i18n.svelte';
	import BookCover from './BookCover.svelte';

	const t = i18n.t;

	// `heading`: the card title's level. h2 where the cards ARE the page's
	// sections (the Articles index); h3 where they sit under a section heading
	// of their own (a topic's "Articles"), so the outline doesn't read as
	// seventeen top-level sections.
	let { article, heading = 'h2' }: { article: ArticleSummary; heading?: 'h2' | 'h3' } =
		$props();

	// The classic the article sends you on to — its cover leads the row, so the
	// shelf shows the books behind the writing rather than a wall of text. A
	// guide is ABOUT that book, so it says "Reader's guide" instead of "Leads to".
	const lead = $derived(article.lead_book);
	const guide = $derived(isGuide(article));
</script>

<!-- A row card (border-tint hover, no lift — see page-design D3). The whole card
     is one link; the taxonomy lives in the index's topic-filter tabs, so the
     card carries only the cover, title, standfirst and a meta line. -->
<a
	class="article-card card-tint rounded-card border border-border bg-surface"
	class:has-cover={lead}
	href={localizeHref(`/articles/${article.slug}/`)}
>
	{#if lead}
		<!-- Decorative: the meta line names the book in words. -->
		<div aria-hidden="true"><BookCover book={lead} /></div>
	{/if}
	<div class="min-w-0">
		<svelte:element this={heading} class="card-title text-h3">{article.h1}</svelte:element>
		{#if article.description}
			<p class="mt-1 line-clamp-3 text-body text-muted sm:line-clamp-none">{article.description}</p>
		{/if}
		<p class="meta">
			{#if guide}{t('book.readersGuide')}<span class="opacity-50">{' · '}</span>{/if}{readingTime(
				article.word_count
			)}{#if lead && !guide}<span class="opacity-50">{' · '}</span><span class="lead"
					>{t('articles.leadsTo').replace('%title%', lead.title)}</span
				>{/if}
		</p>
	</div>
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
		text-decoration: none;
		color: inherit;
	}
	/* With a cover: a small 3:4 cover at the start, the text beside it. */
	.article-card.has-cover {
		display: grid;
		grid-template-columns: 3.5rem minmax(0, 1fr);
		gap: 1rem;
		align-items: start;
	}
	@media (min-width: 640px) {
		.article-card.has-cover {
			grid-template-columns: 4.25rem minmax(0, 1fr);
			gap: 1.25rem;
		}
	}
	.article-card :global(.card-title) {
		color: var(--color-text);
	}
	.meta {
		margin-top: 0.7rem;
		font-family: var(--font-sans);
		font-size: var(--fs-small);
		color: var(--color-muted);
	}
	.meta .lead {
		color: var(--color-text);
		font-weight: 500;
	}
</style>
