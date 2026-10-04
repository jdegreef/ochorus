<script lang="ts">
	import { scrollEdges } from '$lib/actions/scrollEdges';
	import type { SeriesSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, hreflangFor, itemList } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import SeriesCard from '$lib/components/SeriesCard.svelte';
	import SeriesContinue from '$lib/components/SeriesContinue.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import LibraryTabs from '$lib/components/LibraryTabs.svelte';
	import FilterSummary from '$lib/components/FilterSummary.svelte';
	import { audienceBlurb, audienceName, groupByAudience, seriesCompanion } from '$lib/series';
	import { queryChip } from '$lib/filterChips';
	import { SHELF_SEARCH_MIN, matchesQuery } from '$lib/shelfSearch';
	import { urlFilters } from '$lib/urlFilters.svelte';
	import { page } from '$app/stores';

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

	// A filter field once the shelf is long enough to want one — the Topics
	// shelf's row. The query is in the URL like every shelf's.
	const filters = urlFilters({ defaults: { q: '' }, url: () => $page.url });
	const showSearch = $derived(series.length >= SHELF_SEARCH_MIN);
	const filtering = $derived(filters.active);
	const clearFilters = () => filters.reset();
	const shown = $derived.by(() => {
		const q = filters.values.q.trim().toLowerCase();
		return series.filter((s) => matchesQuery(q, s.title, s.description, ...(s.titles ?? [])));
	});
	const activeChips = $derived([queryChip(filters)].filter((c) => c !== null));

	// Grouped by who each series is for. A list with no audience tagged at all
	// (an API behind this build) stays one flat grid rather than a lone
	// "More book series" heading over everything.
	const groups = $derived(groupByAudience(shown));
	const grouped = $derived(groups.some((g) => g.audience));
	// The jump chips' targets: one id per audience group, "more" for the rest.
	const groupId = (audience: string | null) => `audience-${audience ?? 'more'}`;

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

<!-- --pinned-offset: the app nav, the one bar that pins here — what the
     jump-chip targets clear (the authors index adds its controls bar). -->
<div class="page-col px-5 py-10" style="--pinned-offset: var(--appnav-h, 4rem)">
	<LibraryTabs current="series" />
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

	{#snippet clearFiltersAction()}
		<button class="btn btn-ghost" onclick={clearFilters}>{t('common.clearFilters')}</button>
	{/snippet}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if series.length === 0}
		<EmptyState message={t('series.none')} />
	{:else}
		{#if !filtering}
			<SeriesContinue {series} />
		{/if}
		{#if showSearch}
			<div class="filter-row mb-6">
				<input
					bind:value={filters.values.q}
					type="search"
					autocomplete="off"
					class="filter-field grow"
					placeholder={t('series.filterPlaceholder')}
					aria-label={t('series.filterPlaceholder')}
				/>
			</div>
		{/if}
		{#if filtering}
			<FilterSummary
				shown={shown.length}
				total={series.length}
				template={t('series.showing')}
				onClear={clearFilters}
				chips={activeChips}
				class="mb-6"
			/>
		{/if}
		{#if shown.length === 0}
			<EmptyState message={t('series.noResults')} action={clearFiltersAction} />
		{/if}
		{#if grouped && groups.length > 1}
			<!-- One link per audience group: "7 Book Series" with only the young
			     readers' four above the fold left adults guessing whether there
			     was anything for them. Anchors, not a filter — every card stays
			     in the prerendered page. -->
			<nav class="chip-scroller mb-8 flex gap-2" use:scrollEdges aria-label={t('nav.series')}>
				{#each groups as g (g.audience ?? 'more')}
					<a class="tag" href="#{groupId(g.audience)}"
						>{audienceName(g.audience)}<span class="count">{g.series.length}</span></a
					>
				{/each}
			</nav>
		{/if}
		{#each groups as g (g.audience ?? 'more')}
			{@const blurb = audienceBlurb(g.audience)}
			<section id={groupId(g.audience)} class="jump-anchor mb-12">
				{#if grouped}
					<GroupHeading name={audienceName(g.audience)} count={g.series.length} />
					{#if blurb}
						<p class="-mt-2 mb-5 max-w-2xl text-small text-muted">{blurb}</p>
					{/if}
					{#if g.audience === 'young_readers'}
						<!-- The adult choosing for a child: free, no account, and how
						     a family or a class might use these books. -->
						<!-- A labelled aside, not an <h3>: the series cards beside it are
						     the group's h3s, and this isn't one of them. -->
						<aside class="parents-note mb-5 max-w-2xl" aria-labelledby="parents-note">
							<p id="parents-note" class="text-small font-semibold text-text">
								{t('series.parentsHeading')}
							</p>
							<p class="mt-1 text-small text-muted">{t('series.parentsBody')}</p>
						</aside>
					{/if}
				{/if}
				<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
					{#each g.series as s (s.slug)}
						<SeriesCard
							series={s}
							companion={seriesCompanion(s.slug, series)}
							headingLevel={grouped ? 3 : 2}
						/>
					{/each}
				</div>
			</section>
		{/each}
	{/if}
</div>

<style>
	/* Jump targets clear the pinned app nav (the authors and biographies
	   indexes' group sections use the same recipe). */
	.jump-anchor {
		scroll-margin-top: calc(var(--pinned-offset) + 0.5rem);
	}
	/* The note for parents and teachers under "For young readers". */
	.parents-note {
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		padding: 0.85rem 1rem;
	}
</style>
