<script lang="ts">
	import type { PlanSummary } from '$lib/library-public';
	import { planProgress } from '$lib/planProgress.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { SITE_URL } from '$lib/config';
	import { itemList, hreflangAll } from '$lib/seo';
	import { localizeHref } from '$lib/href';
	import ForPromo from '$lib/components/ForPromo.svelte';
	import PlanShelfCard from '$lib/components/PlanShelfCard.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
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
	import { SHELF_SEARCH_MIN, matchesQuery } from '$lib/shelfSearch';
	import { urlFilters } from '$lib/urlFilters.svelte';
	import { page } from '$app/stores';

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

	// Length: the question a reader brings to this shelf is how much time they
	// have, so the shelf is grouped by it (design review #19) — "A week or two"
	// (up to 14 days), "About a month" (15–40), "Longer journeys" — and the same
	// three buckets are the length filter's chips, so a chip and a group heading
	// never disagree about where a plan sits. The query and length live in the
	// URL (shareable/reloadable/Back-able) via $lib/urlFilters, like every shelf.
	type LengthBucket = 'short' | 'medium' | 'long';
	const BUCKETS: LengthBucket[] = ['short', 'medium', 'long'];
	const bucketOf = (days: number): LengthBucket =>
		days <= 14 ? 'short' : days <= 40 ? 'medium' : 'long';
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
	const countIn = (list: PlanSummary[]) => {
		const c: Record<LengthBucket, number> = { short: 0, medium: 0, long: 0 };
		for (const p of list) c[bucketOf(p.day_count)]++;
		return c;
	};
	const counts = $derived(countIn(plans));
	// What the chips count: the plans the search leaves, so pressing "About a
	// month 3" shows three. Which chips exist still follows the whole shelf, so
	// the row doesn't reshuffle while the reader types.
	const matching = $derived.by(() => {
		const q = filters.values.q.trim().toLowerCase();
		return plans.filter((p) => matchesQuery(q, p.title, p.description));
	});
	const matchCounts = $derived(countIn(matching));
	// Only buckets that hold a plan are offered, and the chips only when the
	// plans actually spread across two of them.
	const shownBuckets = $derived(BUCKETS.filter((b) => counts[b] > 0));
	const showSearch = $derived(plans.length >= SHELF_SEARCH_MIN);
	const showLength = $derived(plans.length >= 3 && shownBuckets.length >= 2);
	/** The length choices, said once for the inline chips and the phone sheet. */
	const lengthOptions = $derived([
		{ v: '', label: t('plans.lengthAll'), count: matching.length },
		...shownBuckets.map((b) => ({ v: b, label: t(LENGTH_LABEL[b]), count: matchCounts[b] }))
	]);

	// Sort is a view choice for this visit, and deliberately NOT restored from
	// localStorage: a sorted shelf is a flat list and the resting one is grouped,
	// so restoring it after the prerendered paint flipped the whole page from
	// groups to a list on every load (page-design: never restore a
	// layout-changing preference on a prerendered page — Biographies, 2026-10).
	type Sort = 'shelf' | 'shortest' | 'longest';
	const SORTS: { v: Sort; k: string }[] = [
		{ v: 'shelf', k: 'common.sortShelf' },
		{ v: 'shortest', k: 'common.sortShortest' },
		{ v: 'longest', k: 'common.sortLongest' }
	];
	let sort = $state<Sort>('shelf');
	const setSort = (v: Sort) => (sort = v);

	const filtering = $derived(filters.active);
	const clearFilters = () => filters.reset();
	const filtered = $derived.by(() => {
		const len = filters.values.length;
		return len ? matching.filter((p) => bucketOf(p.day_count) === len) : matching;
	});
	const shownPlans = $derived(
		sort === 'shelf'
			? filtered
			: [...filtered].sort((a, b) =>
					sort === 'shortest' ? a.day_count - b.day_count : b.day_count - a.day_count
				)
	);
	// The resting shelf reads in length groups, in shelf order within each. Once
	// the reader sorts or filters they asked for a list, so they get a flat one.
	// (Resting means unfiltered and unsorted, so the groups split `plans` itself.)
	const groups = $derived(
		filtering || sort !== 'shelf' || !showLength
			? null
			: shownBuckets.map((b) => ({
					bucket: b,
					plans: plans.filter((p) => bucketOf(p.day_count) === b)
				}))
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

<!-- The length chips of the inline row (sm up); the phone sheet offers the
     same choices as SheetChoices. -->
{#snippet lengthChips()}
	<div class="flex flex-wrap gap-1.5" role="group" aria-label={t('plans.lengthAll')}>
		{#each lengthOptions as o (o.v)}
			{@const on = filters.values.length === o.v}
			<button
				type="button"
				class="chip"
				class:active={on}
				aria-pressed={on}
				onclick={() => (filters.values.length = o.v)}
			>
				{o.label}<span class="count">{o.count}</span>
			</button>
		{/each}
	</div>
{/snippet}

{#snippet planGrid(list: PlanSummary[], headingLevel: 2 | 3)}
	<!-- A short group the items can fill two-up (4 plans: "A week or two")
	     stays two across on a desktop: three across left one card alone on
	     its row. Longer groups keep three. -->
	{@const pairs = list.length <= 5 && list.length % 2 === 0}
	<div class="grid items-stretch gap-x-6 gap-y-7 sm:grid-cols-2 {pairs ? '' : 'lg:grid-cols-3'}">
		{#each list as plan (plan.slug)}
			<PlanShelfCard {plan} {headingLevel} />
		{/each}
	</div>
{/snippet}

{#snippet clearFiltersAction()}
	<button class="btn btn-ghost" onclick={clearFilters}>{t('common.clearFilters')}</button>
{/snippet}

<div class="page-col px-5 py-10">
	<PageHeader
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
		<EmptyState art="path" message={t('plans.none')} />
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
							options={lengthOptions}
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
					{#if showLength}{@render lengthChips()}{/if}
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
			<EmptyState art="search" message={t('plans.noResults')} action={clearFiltersAction} />
		{:else if groups}
			{#each groups as g (g.bucket)}
				<section class="mb-12 last:mb-0">
					<GroupHeading name={t(LENGTH_LABEL[g.bucket])} count={g.plans.length} />
					{@render planGrid(g.plans, 3)}
				</section>
			{/each}
		{:else}
			{@render planGrid(shownPlans, 2)}
		{/if}
		<!-- The leader's way on, after the plans rather than in the page head
		     (design review #4): a reader came for the shelf first. Only under
		     real results — never as the answer to an empty filter. -->
		{#if shownPlans.length}
			<ForPromo place="plans-shelf" class="mt-8" />
		{/if}
	{/if}
</div>
