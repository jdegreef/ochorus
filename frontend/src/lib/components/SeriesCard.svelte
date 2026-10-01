<script lang="ts">
	import { onMount } from 'svelte';
	import type { SeriesSummary } from '$lib/library-public';
	import { bookProgressReader } from '$lib/progress';
	import { seriesCardProgressLabel, seriesProgress, splitSeriesTitle } from '$lib/series';
	import { contentLang } from '$lib/reading';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { seriesMeta } from '$lib/emblemNames';
	import { seriesAges } from '$lib/series';
	import ShelfCard from './ShelfCard.svelte';

	/**
	 * A book series as a browse card — the Topics/Plans `ShelfCard`, so the
	 * /series index reads as a sibling of those two shelves, and the Books page's
	 * Book Series rail shows the same card a reader then meets on the index.
	 * `compact` is the rail's form: no description, and an <h3> title because
	 * the rail sits under its own "Book Series" <h2>; the index's cards sit
	 * directly under the page <h1>.
	 */
	let {
		series,
		compact = false,
		headingLevel = compact ? 3 : 2
	}: {
		series: SeriesSummary;
		compact?: boolean;
		/** Overrides the level `compact` implies — the index's full cards sit
		 *  under an audience <h2>, so they title themselves <h3>. */
		headingLevel?: 2 | 3;
	} = $props();
	const t = i18n.t;
	const meta = $derived(seriesMeta(series.slug));

	// The reader's progress through the series, read after mount: it lives in
	// localStorage, and the prerendered card must not bake one visitor's place
	// into every page. Drawn only once a book of the series is begun, as one
	// segment per book — an empty bar over "0 of 4 read" told a reader halfway
	// through book one that they had done nothing.
	let mounted = $state(false);
	onMount(() => (mounted = true));
	const progress = $derived(
		mounted && series.books ? seriesProgress(series.books, bookProgressReader()) : null
	);
	const progressLabel = $derived(
		progress ? seriesCardProgressLabel(progress, contentLang(getLang())) : ''
	);
	const ages = $derived(seriesAges(series));
	// "Rooted – 30 Days with God for Youth" as a name over a subtitle, so the
	// title stays short enough to sit level with the count beside it.
	const heading = $derived(splitSeriesTitle(series.title));
</script>

<ShelfCard
	href={localizeHref(`/series/${series.slug}/`)}
	hue={meta.accent}
	emblem={meta.emblem}
	covers={series.covers}
	title={heading.name}
	{headingLevel}
>
	{#snippet aside()}
		{series.book_count}
		{series.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}
	{/snippet}
	{#if heading.subtitle}
		<p class="mt-0.5 text-small text-muted" dir="auto">{heading.subtitle}</p>
	{/if}
	{#if ages}
		<!-- Ink, not accent: the whole card is one link, and an indigo line
		     inside it read as a second one that went nowhere. -->
		<p class="mt-0.5 text-small font-medium text-text">{ages}</p>
	{/if}
	{#if !compact && series.description}
		<p class="shelf-card-desc series-desc mt-1.5 text-small text-muted" dir="auto">
			{series.description}
		</p>
	{/if}
	{#if progress?.started}
		<!-- mt-auto: with the body's flex:1 this sits on the card's floor, so a
		     row of cards keeps its meters level. -->
		<div class="mt-auto flex flex-col gap-1.5 pt-3">
			<div class="segments" aria-hidden="true">
				{#each progress.stages as stage, i (i)}
					<span class="segment {stage}"></span>
				{/each}
			</div>
			<span class="text-small text-muted">{progressLabel}</span>
		</div>
	{/if}
</ShelfCard>

<style>
	/* Five lines, not the shelf's three: series blurbs run to ~210 characters
	   in English (longer in translation), and at three a three-up grid cut
	   Sons of the King off mid-word. Still a clamp, so no blurb sets a row. */
	.series-desc {
		-webkit-line-clamp: 5;
		line-clamp: 5;
	}
	.segments {
		display: flex;
		gap: 0.25rem;
	}
	.segment {
		flex: 1;
		height: 0.3rem;
		border-radius: 999px;
		background: var(--surface-2);
	}
	.segment.done {
		background: var(--accent);
	}
	.segment.reading {
		background: var(--gold);
	}
</style>
