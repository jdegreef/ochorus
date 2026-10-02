<script lang="ts">
	import { onMount } from 'svelte';
	import type { SavedQuote } from '$lib/library-public';
	import { citeLine } from '$lib/library-public';
	import QuoteCard from '$lib/components/QuoteCard.svelte';
	import { dayIndex } from '$lib/quoteText';
	import { i18n } from '$lib/i18n.svelte';

	// The /quotes index opens on one quotation, fully cited, instead of a list
	// of names: the thing the page promises, shown before anything else. The
	// pool comes from the API (short reviewed lines, writers interleaved).
	// `start` is the day's pick as of the build, baked into the prerendered
	// page; after mount it is re-taken for the reader's own day, which only
	// changes the quote when the day has turned since the deploy.
	let { pool, start = 0 }: { pool: SavedQuote[]; start?: number } = $props();
	const t = i18n.t;

	// svelte-ignore state_referenced_locally
	let at = $state(start);
	const q = $derived(pool[at % pool.length]);

	onMount(() => {
		at = dayIndex(new Date(), pool.length);
	});
</script>

{#if q}
	<section class="featured" aria-labelledby="featured-quote-label">
		<div class="head">
			<span id="featured-quote-label" class="eyebrow label">{t('quotes.featuredEyebrow')}</span>
			{#if pool.length > 1}
				<button class="another" onclick={() => (at = (at + 1) % pool.length)}
					>{t('quotes.another')}</button
				>
			{/if}
		</div>
		<a class="byline" href={`/quotes/${q.author.slug}/`}>{q.author.name}</a>
		<!-- Keyed, so "Another quote" starts the next card closed rather than
		     carrying the last one's open context panel across. -->
		<ul class="list">
			{#key q.slug}
				<QuoteCard quote={q} authorName={q.author.name} cite={citeLine(q)} featured />
			{/key}
		</ul>
	</section>
{/if}

<style>
	.featured {
		margin-bottom: 1.75rem;
	}
	.head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 1rem;
	}
	.label {
		color: var(--color-gold);
	}
	.another {
		border: 1px solid var(--color-border);
		background: var(--color-surface);
		color: var(--color-text);
		border-radius: 999px;
		padding: 0.25rem 0.8rem;
		font-size: var(--fs-small);
		cursor: pointer;
	}
	.another:hover {
		border-color: var(--color-accent);
		color: var(--color-accent);
	}
	.byline {
		display: inline-block;
		margin: 0.35rem 0 0.6rem;
		font-family: var(--font-display, Georgia, serif);
		font-size: var(--fs-h3);
		color: var(--color-text);
		text-decoration: none;
	}
	.byline:hover {
		color: var(--color-accent);
	}
	.list {
		list-style: none;
		margin: 0;
		padding: 0;
	}
</style>
