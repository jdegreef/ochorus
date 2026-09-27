<script lang="ts">
	import { onMount } from 'svelte';
	import type { SeriesSummary } from '$lib/library-public';
	import { bookProgressReader } from '$lib/progress';
	import { seriesProgress, seriesProgressLabel } from '$lib/series';
	import { contentLang } from '$lib/reading';
	import { getLang } from '$lib/lang.svelte';
	import ProgressBar from './ProgressBar.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { seriesMeta } from '$lib/emblemNames';
	import ShelfCard from './ShelfCard.svelte';

	/**
	 * A book series as a browse card — the Topics/Plans `ShelfCard`, so the
	 * /series index reads as a sibling of those two shelves, and the Books page's
	 * Book Series rail shows the same card a reader then meets on the index.
	 * `compact` is the rail's form: no description, and an <h3> title because
	 * the rail sits under its own "Book Series" <h2>; the index's cards sit
	 * directly under the page <h1>.
	 */
	let { series, compact = false }: { series: SeriesSummary; compact?: boolean } = $props();
	const t = i18n.t;
	const meta = $derived(seriesMeta(series.slug));

	// The reader's progress through the series, read after mount: it lives in
	// localStorage, and the prerendered card must not bake one visitor's place
	// into every page. Drawn only once a book of the series is begun.
	let mounted = $state(false);
	onMount(() => (mounted = true));
	const progress = $derived(
		mounted && series.books ? seriesProgress(series.books, bookProgressReader()) : null
	);
	const progressLabel = $derived(
		progress ? seriesProgressLabel(progress.done, progress.total, contentLang(getLang())) : ''
	);
</script>

<ShelfCard
	href={localizeHref(`/series/${series.slug}/`)}
	hue={meta.accent}
	emblem={meta.emblem}
	covers={series.covers}
	title={series.title}
	headingLevel={compact ? 3 : 2}
>
	{#snippet aside()}
		{series.book_count}
		{series.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}
	{/snippet}
	{#if !compact && series.description}
		<p class="shelf-card-desc mt-1.5 text-small text-muted" dir="auto">{series.description}</p>
	{/if}
	{#if progress?.started}
		<!-- mt-auto: with the body's flex:1 this sits on the card's floor, so a
		     row of cards keeps its meters level. -->
		<div class="mt-auto flex flex-col gap-1.5 pt-3">
			<ProgressBar percent={(progress.done / progress.total) * 100} label={progressLabel} />
			<span class="text-small text-muted">{progressLabel}</span>
		</div>
	{/if}
</ShelfCard>
