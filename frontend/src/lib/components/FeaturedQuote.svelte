<script lang="ts">
	import { onMount } from 'svelte';
	import type { SavedQuote } from '$lib/library-public';
	import { citeLine, quoteHref } from '$lib/library-public';
	import { assetUrl } from '$lib/assetUrl';
	import QuoteText from '$lib/components/QuoteText.svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import { dayIndex } from '$lib/quoteText';
	import { i18n } from '$lib/i18n.svelte';

	// The /quotes index opens on one quotation, fully cited, instead of a list
	// of names: the thing the page promises, shown before anything else — set
	// huge on the painting of its book. Its source link opens the paragraph. The
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
	{@const art = q.source.kind === 'chapter' ? assetUrl(`/covers/art/${q.source.slug}-640.webp`) : ''}
	<!-- The line set large on the painting of the book it comes from (every
	     painted book has a wordless ground under /covers/art), under a scrim so
	     the type holds on any picture. A sermon has no painting: the dark
	     ground alone. -->
	<section
		class="featured"
		aria-labelledby="featured-quote-label"
		style:--art={art ? `url("${art}")` : undefined}
	>
		<div class="head">
			<span id="featured-quote-label" class="eyebrow label">{t('quotes.featuredEyebrow')}</span>
			{#if pool.length > 1}
				<button class="another" onclick={() => (at = (at + 1) % pool.length)}
					>{t('quotes.another')}</button
				>
			{/if}
		</div>
		{#key q.slug}
			<figure class="hero">
				<blockquote><p>“<QuoteText text={q.text} />”</p></blockquote>
				<figcaption>
					<a class="byline" href={`/quotes/${q.author.slug}/`}>{q.author.name}</a>
					<a class="cite" href={quoteHref(q)}><cite>{citeLine(q)}</cite> <Arrow /></a>
				</figcaption>
			</figure>
		{/key}
	</section>
{/if}

<style>
	/* hex-ok-file: the scrim and the type on it are the painting's, not the
	   theme's — white on a darkened picture reads the same in light and dark. */
	.featured {
		position: relative;
		isolation: isolate;
		overflow: hidden;
		margin-bottom: 1.75rem;
		padding: 1.25rem 1.5rem 1.75rem;
		border-radius: var(--radius-card);
		background: #1d1a16;
		color: #fff;
	}
	.featured::before {
		content: '';
		position: absolute;
		inset: 0;
		z-index: -1;
		background:
			linear-gradient(180deg, rgb(15 12 9 / 0.55), rgb(15 12 9 / 0.82)),
			var(--art, none) center / cover no-repeat;
	}
	@media (min-width: 640px) {
		.featured {
			padding: 1.5rem 2.5rem 2.5rem;
		}
		.hero blockquote {
			font-size: var(--fs-h1);
		}
	}
	.head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 1rem;
	}
	.label {
		color: #f0d68c;
	}
	.another {
		border: 1px solid rgb(255 255 255 / 0.4);
		background: rgb(255 255 255 / 0.08);
		color: #fff;
		border-radius: var(--radius-pill);
		padding: 0.25rem 0.8rem;
		font-size: var(--fs-small);
		white-space: nowrap;
		cursor: pointer;
	}
	.another:hover {
		background: rgb(255 255 255 / 0.18);
	}
	.hero {
		margin: 1.75rem 0 0;
		max-width: 46rem;
	}
	.hero blockquote {
		margin: 0;
		font-family: var(--font-display);
		font-size: var(--fs-h2);
		line-height: 1.25;
		text-wrap: balance;
		text-shadow: 0 1px 12px rgb(0 0 0 / 0.35);
	}
	.hero figcaption {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.25rem 1rem;
		margin-top: 1.25rem;
	}
	.byline {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		color: #fff;
		text-decoration: none;
	}
	.cite {
		font-size: var(--fs-small);
		color: rgb(255 255 255 / 0.8);
		text-decoration: none;
	}
	.byline:hover,
	.cite:hover {
		text-decoration: underline;
	}
</style>
