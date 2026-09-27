<script lang="ts">
	import type { SeriesSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, hreflangFor, itemList } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import SeriesCard from '$lib/components/SeriesCard.svelte';

	/**
	 * Every book series in this language — the Topics shelf's anatomy and card,
	 * so the index reads as a sibling of Topics and Plans. Hangs off Books (the
	 * breadcrumb in its JSON-LD, the shelf and count on /books), not the top nav.
	 */
	let { data } = $props();
	const series = $derived<SeriesSummary[]>(data.series);
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;

	const bookTotal = $derived(series.reduce((n, s) => n + s.book_count, 0));

	// schema.org ItemList of the series: each entry is the series page, whose own
	// BookSeries LD names its parts.
	const seriesLd = $derived(
		itemList(
			t('nav.series'),
			series.map((s) => ({ name: s.title, url: localizeHref(`/series/${s.slug}/`) }))
		)
	);
	const crumbsLd = $derived(
		breadcrumbLd([
			{ name: t('common.home'), href: '/' },
			{ name: t('nav.books'), href: '/books' },
			{ name: t('nav.series'), href: '/series/' }
		])
	);
	// Only the languages with a series (the sitemap lists the same set). A locale
	// with none still bakes this page — the footer links it everywhere — but as
	// an unindexed empty shelf that claims no alternates: hreflangFor would
	// otherwise fall back to advertising every locale. `?? []` covers a list from
	// an API that predates the field (the web build can run before the API's).
	const languages = $derived([...new Set(series.flatMap((s) => s.languages ?? []))]);
	const hreflang = $derived(
		languages.length
			? hreflangFor('/series/', languages)
			: { alternates: [], xDefault: `${SITE_URL}${localizeHref('/series/', { locale: 'en' })}` }
	);
	const canonical = `${SITE_URL}${localizeHref('/series/')}`;
</script>

<Seo
	title={`${t('nav.series')} — Ochorus`}
	description={t('series.tagline')}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/books.png`}
	structuredData={series.length ? [seriesLd, crumbsLd] : [crumbsLd]}
/>

<svelte:head>
	{#if !series.length}
		<meta name="robots" content="noindex" />
	{/if}
</svelte:head>

<div class="page-col px-5 py-10">
	<PageHeader
		title={t('nav.series')}
		tagline={t('series.tagline')}
		meta={series.length ? counts : undefined}
	/>
	{#snippet counts()}
		{series.length}
		{series.length === 1 ? t('common.seriesOne') : t('common.seriesMany')}
		<span class="opacity-50">·</span>
		{bookTotal}
		{bookTotal === 1 ? t('common.bookOne') : t('common.bookMany')}
	{/snippet}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if series.length === 0}
		<EmptyState message={t('series.none')} />
	{:else}
		<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
			{#each series as s (s.slug)}
				<SeriesCard series={s} />
			{/each}
		</div>
	{/if}
</div>
