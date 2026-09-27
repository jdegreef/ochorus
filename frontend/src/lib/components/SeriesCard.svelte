<script lang="ts">
	import type { SeriesSummary } from '$lib/library-public';
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
</ShelfCard>
