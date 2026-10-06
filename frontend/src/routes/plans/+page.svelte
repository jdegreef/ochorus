<script lang="ts">
	import type { PlanSummary } from '$lib/library-public';
	import { planProgress } from '$lib/planProgress.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { SITE_URL } from '$lib/config';
	import { itemList, hreflangAll } from '$lib/seo';
	import { localizeHref } from '$lib/href';
	import PlanShelfCard from '$lib/components/PlanShelfCard.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import ContinueShelf from '$lib/components/ContinueShelf.svelte';
	import ContinueRow from '$lib/components/ContinueRow.svelte';
	import FilterSummary from '$lib/components/FilterSummary.svelte';
	import FilterSheet from '$lib/components/FilterSheet.svelte';
	import SheetChoices from '$lib/components/SheetChoices.svelte';
	import { planMeta } from '$lib/emblemNames';
	import { queryChip, type FilterChip } from '$lib/filterChips';
	import { readJSON, writeJSON } from '$lib/persisted';
	import { SHELF_SEARCH_MIN, matchesQuery } from '$lib/shelfSearch';
	import { urlFilters } from '$lib/urlFilters.svelte';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';

	let { data } = $props();
	const plans = $derived<PlanSummary[]>(data.plans);
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;

	// Hoisted for the "Continue your plans" rows (i18n.t is an uncached lookup);
	// the shelf's own cards are PlanShelfCard, which hoists its own.
	const OF = t('plans.of');
	const DAYS = t('plans.days');
	const DAY = t('plans.day');
	/** The progress bar's accessible name — the visible caption, in words. */
	const dayLabel = (plan: PlanSummary, done: number) =>
		`${plan.title}: ${done} ${OF} ${plan.day_count} ${DAYS}`;

	// Length filter: help a reader pick a plan that fits the time they have, and
	// keep the list scannable as it grows. Buckets are derived from the day count
	// — up to two weeks, up to a month, longer — and labelled with that time, as
	// the Sermons length filter is. The query and length live in the URL
	// (shareable/reloadable/Back-able) via $lib/urlFilters, like every shelf.
	type LengthBucket = 'short' | 'medium' | 'long';
	const BUCKETS: LengthBucket[] = ['short', 'medium', 'long'];
	const bucketOf = (days: number): LengthBucket =>
		days <= 14 ? 'short' : days <= 30 ? 'medium' : 'long';
	const LENGTH_LABEL: Record<LengthBucket, string> = {
		short: 'plans.lengthShort',
		medium: 'plans.lengthMedium',
		long: 'plans.lengthLong'
	};
	const filters = urlFilters({
		defaults: { q: '', length: '' },
		allowed: { length: BUCKETS },
		url: () => $page.url
	});
	const counts = $derived.by(() => {
		const c: Record<LengthBucket, number> = { short: 0, medium: 0, long: 0 };
		for (const p of plans) c[bucketOf(p.day_count)]++;
		return c;
	});
	// Only buckets that hold a plan are offered, and the dropdown only when the
	// plans actually spread across two of them.
	const shownBuckets = $derived(BUCKETS.filter((b) => counts[b] > 0));
	const showSearch = $derived(plans.length >= SHELF_SEARCH_MIN);
	const showLength = $derived(plans.length >= 3 && shownBuckets.length >= 2);

	// Sort is the reader's preference, not the shelf's: localStorage.
	type Sort = 'shelf' | 'shortest' | 'longest';
	const SORTS: { v: Sort; k: string }[] = [
		{ v: 'shelf', k: 'common.sortShelf' },
		{ v: 'shortest', k: 'common.sortShortest' },
		{ v: 'longest', k: 'common.sortLongest' }
	];
	const PREFS_KEY = 'ochorus:plans-view';
	let sort = $state<Sort>('shelf');
	onMount(() => {
		const p = readJSON<{ sort?: Sort }>(PREFS_KEY, {});
		if (p.sort && SORTS.some((o) => o.v === p.sort)) sort = p.sort;
	});
	const setSort = (v: Sort) => {
		sort = v;
		writeJSON(PREFS_KEY, { sort });
	};

	const filtering = $derived(filters.active);
	const clearFilters = () => filters.reset();
	const filtered = $derived.by(() => {
		const q = filters.values.q.trim().toLowerCase();
		const len = filters.values.length;
		return plans.filter(
			(p) => (!len || bucketOf(p.day_count) === len) && matchesQuery(q, p.title, p.description)
		);
	});
	const shownPlans = $derived(
		sort === 'shelf'
			? filtered
			: [...filtered].sort((a, b) =>
					sort === 'shortest' ? a.day_count - b.day_count : b.day_count - a.day_count
				)
	);
	const activeChips = $derived.by(() => {
		const c: FilterChip[] = [];
		const q = queryChip(filters);
		if (q) c.push(q);
		const len = filters.values.length as LengthBucket | '';
		if (len) c.push({ kind: 'length', label: t(LENGTH_LABEL[len]), onRemove: () => (filters.values.length = '') });
		return c;
	});

	// Self-referential canonical + hreflang per locale (mirrors /books, /topics).
	// schema.org ItemList of the plans shelf — an ordered roster for crawlers.
	const plansLd = $derived(
		itemList(
			t('plans.title'),
			plans.map((p) => ({ name: p.title, url: localizeHref(`/plans/${p.slug}`) }))
		)
	);

	const canonical = `${SITE_URL}${localizeHref('/plans')}`;
	// Gated on ADVERTISED_LOCALES, not Paraglide's full `locales`: a locale that
	// is wired in the UI but has an empty catalog must not be advertised to
	// crawlers (see advertised-locales.ts). This page was claiming alternates
	// for draft locales while sitemap.xml, the detail pages and the footer all
	// correctly omitted them — two contradictory claims, with the wrong one on
	// the site's most-crawled pages.
	const hreflang = hreflangAll('/plans');

	// "Continue your plans" hub: the reader's started-but-unfinished plans,
	// most recently started first, so a daily reader lands straight on where
	// they left off instead of re-hunting through the catalogue. `started()`
	// exposes this ordering; join it against the loaded plan metadata.
	const bySlug = $derived(new Map(plans.map((p) => [p.slug, p])));
	const activePlans = $derived.by(() => {
		void planProgress.ticks;
		return planProgress
			.started()
			.map((s) => bySlug.get(s.slug))
			.filter(
				(p): p is PlanSummary =>
					!!p && planProgress.doneDays(p.slug).length < p.day_count
			);
	});
</script>

<Seo
	title={`${t('plans.title')} — Ochorus`}
	description={t('plans.tagline')}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/plans.png`}
	structuredData={plans.length ? [plansLd] : []}
/>

<!-- Shared by the inline row (sm up) and the phone sheet. -->
{#snippet lengthSelect(cls: string)}
	<select bind:value={filters.values.length} aria-label={t('plans.lengthAll')} class="filter-field {cls}">
		<option value="">{t('plans.lengthAll')}</option>
		{#each shownBuckets as b (b)}
			<option value={b}>{t(LENGTH_LABEL[b])} ({counts[b]})</option>
		{/each}
	</select>
{/snippet}

{#snippet clearFiltersAction()}
	<button class="btn btn-ghost" onclick={clearFilters}>{t('common.clearFilters')}</button>
{/snippet}

<div class="page-col px-5 py-10">
	<PageHeader
		section="plans"
		title={t('plans.title')}
		tagline={t('plans.tagline')}
		meta={plans.length ? planCounts : undefined}
	/>
	{#snippet planCounts()}
		{plans.length}
		{plans.length === 1 ? t('common.planOne') : t('common.planMany')}
	{/snippet}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if plans.length === 0}
		<EmptyState message={t('plans.none')} />
	{:else}
		<!-- Continue your plans: pick up where you left off. Only shown when the
		     reader has an unfinished plan in progress, and not while filtering. -->
		{#if activePlans.length && !filtering}
			<ContinueShelf heading={t('plans.continueHeading')}>
				{#each activePlans as plan (plan.slug)}
					{@const done = planProgress.doneDays(plan.slug).length}
					{@const next = planProgress.nextDay(plan.slug, plan.day_count)}
					{@const meta = planMeta(plan.slug)}
					<ContinueRow
						href={localizeHref(`/plans/${plan.slug}`)}
						title={plan.title}
						caption={`${DAY} ${next} ${OF} ${plan.day_count}`}
						verb={t('plans.continue')}
						hue={meta.accent}
						emblem={meta.emblem}
					>
						{#snippet progress()}
							<ProgressBar percent={(done / plan.day_count) * 100} label={dayLabel(plan, done)} />
						{/snippet}
					</ContinueRow>
				{/each}
			</ContinueShelf>
		{/if}

		{#if showSearch || showLength}
			<div class="filter-row mb-6">
				{#if showSearch}
					<input
						bind:value={filters.values.q}
						type="search"
						autocomplete="off"
						class="filter-field grow"
						placeholder={t('plans.filterPlaceholder')}
						aria-label={t('plans.filterPlaceholder')}
					/>
				{/if}
				<!-- Phone only: the same controls, as one-tap choices in a sheet. -->
				<FilterSheet
					count={filters.values.length ? 1 : 0}
					shown={filtered.length}
					showLabel={t('plans.showResults')}
					filtered={filtering}
					onClear={clearFilters}
				>
					{#if showLength}
						<SheetChoices
							label={t('plans.lengthAll')}
							showLabel={false}
							options={[
								{ v: '', label: t('plans.lengthAll') },
								...shownBuckets.map((b) => ({ v: b, label: t(LENGTH_LABEL[b]), count: counts[b] }))
							]}
							value={filters.values.length}
							onselect={(v) => (filters.values.length = v)}
						/>
					{/if}
					<SheetChoices
						label={t('common.sort')}
						options={SORTS.map((o) => ({ v: o.v, label: t(o.k) }))}
						value={sort}
						onselect={setSort}
					/>
				</FilterSheet>
				<div class="hidden sm:contents">
					{#if showLength}{@render lengthSelect('')}{/if}
					<select
						value={sort}
						onchange={(e) => setSort(e.currentTarget.value as Sort)}
						class="filter-field"
						aria-label={t('common.sort')}
					>
						{#each SORTS as o (o.v)}
							<option value={o.v}>{t(o.k)}</option>
						{/each}
					</select>
				</div>
			</div>
		{/if}

		{#if filtering}
			<FilterSummary
				shown={filtered.length}
				total={plans.length}
				template={t('plans.showing')}
				onClear={clearFilters}
				chips={activeChips}
				class="mb-6"
			/>
		{/if}

		{#if shownPlans.length === 0}
			<EmptyState message={t('plans.noResults')} action={clearFiltersAction} />
		{:else}
			<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
				{#each shownPlans as plan (plan.slug)}
					<PlanShelfCard {plan} />
				{/each}
			</div>
		{/if}
	{/if}
</div>
