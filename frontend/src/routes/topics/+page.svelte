<script lang="ts">
	import type { TopicSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { itemList, hreflangAll } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import ShelfCard from '$lib/components/ShelfCard.svelte';
	import { passageMark } from '$lib/sermonMonogram';
	import { topicMeta } from '$lib/emblemNames';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import FilterSummary from '$lib/components/FilterSummary.svelte';
	import { queryChip } from '$lib/filterChips';
	import { SHELF_SEARCH_MIN, matchesQuery } from '$lib/shelfSearch';
	import { urlFilters } from '$lib/urlFilters.svelte';
	import { page } from '$app/stores';

	let { data } = $props();
	const topics = $derived<TopicSummary[]>(data.topics);
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;

	// A filter field once the shelf is long enough to want one (page-design:
	// every shelf opens with the same row). The query lives in the URL, as on
	// every shelf, so a filtered view survives a reload and comes back with Back.
	const filters = urlFilters({ defaults: { q: '' }, url: () => $page.url });
	const showSearch = $derived(topics.length >= SHELF_SEARCH_MIN);
	const filtering = $derived(filters.active);
	const clearFilters = () => filters.reset();
	const shown = $derived.by(() => {
		const q = filters.values.q.trim().toLowerCase();
		return topics.filter((tp) => matchesQuery(q, tp.title, tp.description));
	});
	const activeChips = $derived([queryChip(filters)].filter((c) => c !== null));

	// schema.org ItemList of the topical shelves — an ordered roster for crawlers.
	const topicsLd = $derived(
		itemList(
			t('topics.title'),
			topics.map((tp) => ({ name: tp.title, url: localizeHref(`/topics/${tp.slug}`) }))
		)
	);


	// Gated on ADVERTISED_LOCALES, not Paraglide's full `locales`: a locale that
	// is wired in the UI but has an empty catalog must not be advertised to
	// crawlers (see advertised-locales.ts). This page was claiming alternates
	// for draft locales while sitemap.xml, the detail pages and the footer all
	// correctly omitted them — two contradictory claims, with the wrong one on
	// the site's most-crawled pages.
	const hreflang = hreflangAll('/topics');
	const canonical = `${SITE_URL}${localizeHref('/topics')}`;
</script>

<Seo
	title={`${t('topics.title')} — Ochorus`}
	description={t('topics.tagline')}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/topics.png`}
	structuredData={topics.length ? [topicsLd] : []}
/>

<div class="page-col px-5 py-10">
	<PageHeader
		title={t('topics.title')}
		tagline={t('topics.tagline')}
		meta={topics.length ? topicCounts : undefined}
	/>
	{#snippet topicCounts()}
		{topics.length}
		{topics.length === 1 ? t('common.topicOne') : t('common.topicMany')}
	{/snippet}

	{#snippet clearFiltersAction()}
		<button class="btn btn-ghost" onclick={clearFilters}>{t('common.clearFilters')}</button>
	{/snippet}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if topics.length === 0}
		<EmptyState message={t('topics.none')} />
	{:else}
		{#if showSearch}
			<div class="filter-row mb-6">
				<input
					bind:value={filters.values.q}
					type="search"
					autocomplete="off"
					class="filter-field grow"
					placeholder={t('topics.filterPlaceholder')}
					aria-label={t('topics.filterPlaceholder')}
				/>
			</div>
		{/if}
		{#if filtering}
			<FilterSummary
				shown={shown.length}
				total={topics.length}
				template={t('topics.showing')}
				onClear={clearFilters}
				chips={activeChips}
				class="mb-6"
			/>
		{/if}
		{#if shown.length === 0}
			<EmptyState message={t('topics.noResults')} action={clearFiltersAction} />
		{/if}
		<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
			{#each shown as topic (topic.slug)}
				{@const meta = topicMeta(topic.slug)}
				<ShelfCard
					href={localizeHref(`/topics/${topic.slug}`)}
					hue={meta.accent}
					emblem={meta.emblem}
					mark={passageMark(topic.scripture_ref)}
					covers={topic.covers}
					title={topic.title}
				>
					{#snippet aside()}
						<!-- The book count is dropped when it is zero rather than printed as
						     "0 books · 5 sermons". A shelf listed on the strength of its
						     sermons is most shelves in most languages (see
						     TopicListSerializer.get_covers), and announcing what it does
						     NOT have first is how this card came to contradict itself. -->
						{#if topic.book_count}
							{topic.book_count}
							{topic.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}
						{/if}
						{#if topic.sermon_count}
							{#if topic.book_count}<span class="opacity-50"> · </span>{/if}{topic.sermon_count}
							{topic.sermon_count === 1 ? t('common.sermonOne') : t('common.sermonMany')}
						{/if}
					{/snippet}
					<p class="shelf-card-desc mt-1.5 text-small text-muted">{topic.description}</p>
				</ShelfCard>
			{/each}
		</div>
	{/if}
</div>

