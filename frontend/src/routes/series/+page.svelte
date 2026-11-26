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
	import SeriesContinue from '$lib/components/SeriesContinue.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import LibraryTabs from '$lib/components/LibraryTabs.svelte';
	import FilterSummary from '$lib/components/FilterSummary.svelte';
	import {
		audienceBlurb,
		audienceName,
		groupByAudience,
		seriesCompanion,
		splitSeriesTitle
	} from '$lib/series';
	import { hubFor } from '$lib/audienceHub';
	import Arrow from '$lib/components/Arrow.svelte';
	import ParentsNote from '$lib/components/ParentsNote.svelte';
	import { queryChip } from '$lib/filterChips';
	import { SHELF_SEARCH_MIN, matchesQuery } from '$lib/shelfSearch';
	import { urlFilters } from '$lib/urlFilters.svelte';
	import { page } from '$app/stores';
	import * as m from '$lib/paraglide/messages.js';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import { readingLadder } from '$lib/seriesLadder';

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
	// The doors' covers: the first volume of each of the group's first series.
	const doorCovers = (g: { series: SeriesSummary[] }) =>
		g.series.flatMap((s) => s.covers.slice(0, 1)).slice(0, 3);
	const ladder = $derived(readingLadder(series));

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
	<PageHeader
		title={t('nav.series')}
		tagline={t('series.tagline')}
		meta={series.length ? counts : undefined}
	/>
	{#snippet counts()}
		{i18n.count(series.length, 'common.seriesOne', 'common.seriesMany')}
		<span class="sep">·</span>
		{i18n.count(bookTotal, 'common.bookOne', 'common.bookMany')}
	{/snippet}
	<!-- The library tabs sit under the title, as on /books (design review #4). -->
	<LibraryTabs current="series" />

	{#snippet clearFiltersAction()}
		<button class="btn btn-ghost" onclick={clearFilters}>{t('common.clearFilters')}</button>
	{/snippet}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if series.length === 0}
		<EmptyState art="language" message={t('series.none')} />
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
			<EmptyState art="search" message={t('series.noResults')} action={clearFiltersAction} />
		{/if}
		{#if grouped && groups.length > 1}
			<!-- Three doors, one per reader — "who is this for?" before the shelf.
			     Anchors, not a filter: every card stays in the prerendered page. -->
			<nav class="doors mb-10" aria-label={t('nav.series')}>
				{#each groups as g (g.audience ?? 'more')}
					<a class="door card-lift" href="#{groupId(g.audience)}">
						<span class="door-covers" aria-hidden="true"><CoverStrip covers={doorCovers(g)} max={3} /></span>
						<span class="door-name font-display">{audienceName(g.audience)}</span>
						<span class="text-small text-muted"
							>{i18n.count(g.series.length, 'common.seriesOne', 'common.seriesMany')} <Arrow /></span
						>
					</a>
				{/each}
			</nav>
		{/if}
		{#if !filtering && ladder.length > 2}
			<!-- The reading ladder: the series as rungs from six to grown-up. -->
			<section class="mb-12" aria-labelledby="ladder-heading">
				<h2 id="ladder-heading" class="section-label">{t('series.ladderHeading')}</h2>
				<p class="-mt-1 mb-4 max-w-2xl text-small text-muted">{t('series.ladderNote')}</p>
				<ol class="ladder" style="--rungs: {ladder.length}">
					{#each ladder as r, i (r.min ?? 'adults')}
						<li class="rung" style="--step: {i}">
							<span class="rung-age font-display"
								>{r.min == null ? audienceName('adults') : m.series_ages_from({ min: r.min })}</span
							>
							<span class="rung-series">
								{#each r.series as s (s.slug)}
									<a href={localizeHref(`/series/${s.slug}/`)}>{splitSeriesTitle(s.title).name}</a>
								{/each}
							</span>
						</li>
					{/each}
				</ol>
			</section>
		{/if}
		{#each groups as g (g.audience ?? 'more')}
			{@const blurb = audienceBlurb(g.audience)}
			{@const hub = hubFor(g.audience)}
			<section id={groupId(g.audience)} class="jump-anchor mb-12">
				{#if grouped}
					<GroupHeading name={audienceName(g.audience)} count={g.series.length} />
					{#if blurb}
						<p class="-mt-2 mb-5 max-w-2xl text-small text-muted">{blurb}</p>
					{/if}
					{#if hub}
						<!-- The hub gathers this group's series with the retold classics and
						     plans for the same readers ($lib/audienceHub). -->
						<p class="-mt-2 mb-5 text-small">
							<a href={localizeHref(hub.href)} class="text-accent hover:underline"
								>{t(hub.seeKey)} <Arrow /></a
							>
						</p>
					{/if}
					{#if g.audience === 'young_readers'}
						<!-- The adult choosing for a child: free, no account, and how
						     a family or a class might use these books. -->
						<!-- A labelled aside, not an <h3>: the series cards beside it are
						     the group's h3s, and this isn't one of them. -->
						<ParentsNote labelledby="parents-note" class="mb-5 max-w-2xl">
							<p id="parents-note" class="text-small font-semibold text-text">
								{t('series.parentsHeading')}
							</p>
							<p class="mt-1 text-small text-muted">{t('series.parentsBody')}</p>
						</ParentsNote>
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
	.doors {
		display: grid;
		gap: 0.75rem;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr));
	}
	.door {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		padding: 1.1rem 1.25rem 1.25rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		color: var(--text);
		text-decoration: none;
	}
	.door-covers {
		margin-bottom: 0.5rem;
	}
	.door-name {
		font-size: var(--fs-h3);
		font-weight: 600;
		line-height: 1.2;
	}
	/* The ladder: rungs climbing to the end on a wide screen (each one a step
	   higher), a plain stack on a phone. */
	.ladder {
		display: grid;
		gap: 0.5rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.rung {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		padding: 0.75rem 1rem;
		border-inline-start: 3px solid var(--accent);
		background: var(--surface);
		border-radius: var(--radius-sm);
	}
	.rung-age {
		font-weight: 600;
		color: var(--accent);
	}
	.rung-series {
		display: flex;
		flex-wrap: wrap;
		gap: 0.15rem 0.9rem;
		font-size: var(--fs-small);
	}
	.rung-series a {
		color: var(--text);
	}
	.rung-series a:hover {
		color: var(--accent);
	}
	@media (min-width: 768px) {
		.ladder {
			grid-auto-flow: column;
			grid-auto-columns: minmax(0, 1fr);
			align-items: start;
		}
		.rung {
			margin-block-start: calc((var(--rungs) - 1 - var(--step)) * 1.5rem);
			min-height: 6rem;
			border-inline-start: 0;
			border-block-start: 3px solid var(--accent);
		}
	}
	/* Jump targets clear the pinned app nav (the authors and biographies
	   indexes' group sections use the same recipe). */
	.jump-anchor {
		scroll-margin-top: calc(var(--pinned-offset) + 0.5rem);
	}
</style>
