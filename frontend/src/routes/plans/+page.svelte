<script lang="ts">
	import type { PlanSummary } from '$lib/library';
	import { planProgress } from '$lib/planProgress.svelte';
	import { readingMinutes } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { SITE_URL } from '$lib/config';
	import { itemList } from '$lib/seo';
	import { localizeHref } from '$lib/href';
	import { locales } from '$lib/paraglide/runtime';
	import ShelfCard from '$lib/components/ShelfCard.svelte';
	import { planMeta } from '$lib/emblemNames';
	import CatalogLanguageNudge from '$lib/components/CatalogLanguageNudge.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';

	let { data } = $props();
	const plans = $derived<PlanSummary[]>(data.plans);
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;

	// Hoisted: these two ran per plan card, twice (the visible line and the bar's
	// label), and i18n.t is an uncached lookup.
	const OF = t('plans.of');
	const DAYS = t('plans.days');
	/** The progress bar's accessible name — the visible caption, in words. */
	const dayLabel = (plan: PlanSummary, done: number) =>
		`${plan.title}: ${done} ${OF} ${plan.day_count} ${DAYS}`;

	// Length filter: help a reader pick a plan that fits the time they have, and
	// keep the list scannable as it grows. Buckets are derived from the day count
	// — short (up to two weeks), medium (up to a month), long (a month or more).
	type LengthBucket = 'all' | 'short' | 'medium' | 'long';
	const BUCKETS: LengthBucket[] = ['all', 'short', 'medium', 'long'];
	const bucketOf = (days: number): Exclude<LengthBucket, 'all'> =>
		days <= 14 ? 'short' : days <= 30 ? 'medium' : 'long';
	let lengthFilter = $state<LengthBucket>('all');
	const counts = $derived.by(() => {
		const c: Record<string, number> = { all: plans.length, short: 0, medium: 0, long: 0 };
		for (const p of plans) c[bucketOf(p.day_count)]++;
		return c;
	});
	const shownPlans = $derived(
		lengthFilter === 'all' ? plans : plans.filter((p) => bucketOf(p.day_count) === lengthFilter)
	);
	// Only offer the filter once there are enough plans (and enough spread) for it
	// to earn its place; a two-plan list doesn't need filtering.
	const showLengthFilter = $derived(
		plans.length >= 3 && BUCKETS.filter((b) => b !== 'all' && counts[b] > 0).length >= 2
	);

	// Self-referential canonical + hreflang per locale (mirrors /books, /topics).
	// schema.org ItemList of the plans shelf — an ordered roster for crawlers.
	const plansLd = $derived(
		itemList(
			t('plans.title'),
			plans.map((p) => ({ name: p.title, url: localizeHref(`/plans/${p.slug}`) }))
		)
	);

	const canonical = `${SITE_URL}${localizeHref('/plans')}`;
	const alternates = locales.map((loc) => ({
		loc,
		href: `${SITE_URL}${localizeHref('/plans', { locale: loc })}`
	}));

	// Each plan wears a curated accent + emblem — see planMeta in $lib/emblems.

	/** Rounded minutes of reading in an average day of a plan. */
	const perDay = (plan: PlanSummary) =>
		plan.day_count ? Math.max(1, readingMinutes(Math.round(plan.total_words / plan.day_count))) : 0;

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

<svelte:head>
	<title>{t('plans.title')} — Ochorus</title>
	<meta name="description" content={t('plans.tagline')} />
	<link rel="canonical" href={canonical} />
	{#each alternates as a (a.loc)}
		<link rel="alternate" hreflang={a.loc} href={a.href} />
	{/each}
	<link rel="alternate" hreflang="x-default" href="{SITE_URL}/plans" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="{t('plans.title')} — Ochorus" />
	<meta property="og:description" content={t('plans.tagline')} />
	<meta property="og:url" content={canonical} />
	<meta property="og:image" content="{SITE_URL}/og/plans.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{#if plans.length}{@html plansLd}{/if}
</svelte:head>

<div class="page-col px-5 py-10">
	<PageHeader title={t('plans.title')} tagline={t('plans.tagline')} />

	<CatalogLanguageNudge kind="plans" localizedCount={plans.length} />

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if plans.length === 0}
		<EmptyState message={t('plans.none')} />
	{/if}

	<!-- Continue your plans: pick up where you left off. Only shown when the
	     reader has an unfinished plan in progress. -->
	{#if activePlans.length}
		<section class="mb-8">
			<h2 class="section-label">
				{t('plans.continueHeading')}
			</h2>
			<div class="space-y-3">
				{#each activePlans as plan (plan.slug)}
					{@const done = planProgress.doneDays(plan.slug).length}
					<a
						href={localizeHref(`/plans/${plan.slug}`)}
						class="block rounded-card border border-accent-soft bg-surface-2 p-4 hover:bg-surface hover:no-underline"
					>
						<div class="flex items-baseline justify-between gap-3">
							<h3 class="text-body font-semibold text-text">{plan.title}</h3>
							<span class="shrink-0 text-small text-accent">
								{t('plans.day')}
								{planProgress.nextDay(plan.slug, plan.day_count)}
								{t('plans.of')}
								{plan.day_count} →
							</span>
						</div>
						<div class="mt-2">
							<ProgressBar percent={(done / plan.day_count) * 100} label={dayLabel(plan, done)} />
						</div>
					</a>
				{/each}
			</div>
		</section>
	{/if}

	{#if showLengthFilter}
		<div class="filter-row mb-6" role="group" aria-label={t('plans.filterLength')}>
			<span class="me-1 text-small text-muted">{t('plans.filterLength')}</span>
			{#each BUCKETS as b (b)}
				{#if b === 'all' || counts[b] > 0}
					<button
						type="button"
						class="chip"
						class:active={lengthFilter === b}
						onclick={() => (lengthFilter = b)}
						aria-pressed={lengthFilter === b}
					>
						{t(`plans.length_${b}`)}
						<span class="tabular-nums opacity-70">{counts[b]}</span>
					</button>
				{/if}
			{/each}
		</div>
	{/if}

	<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
		{#each shownPlans as plan (plan.slug)}
			{@const done = planProgress.doneDays(plan.slug).length}
			{@const started = planProgress.isStarted(plan.slug)}
			{@const meta = planMeta(plan.slug)}
			<ShelfCard
				href={localizeHref(`/plans/${plan.slug}`)}
				hue={meta.accent}
				emblem={meta.emblem}
				covers={plan.covers}
				title={plan.title}
			>
				{#snippet aside()}
					{plan.day_count} {t('plans.days')}{#if plan.total_words}
						<span class="opacity-60"> · </span>~{perDay(plan)} {t('plans.minPerDay')}{/if}
				{/snippet}
				<p class="shelf-card-desc mt-1.5 text-small text-muted">{plan.description}</p>
				<!-- Pushed to the bottom of the body so every card's footer sits on the
				     same line regardless of description length. -->
				<div class="mt-auto pt-3">
					{#if started}
						<ProgressBar percent={(done / plan.day_count) * 100} label={dayLabel(plan, done)} />
						<p class="mt-1.5 text-small text-muted">
							{done === plan.day_count
								? t('plans.finished')
								: `${t('plans.day')} ${planProgress.nextDay(plan.slug, plan.day_count)} ${t('plans.of')} ${plan.day_count}`}
						</p>
					{:else if plan.day_one}
						<p class="text-small text-muted">
							<span class="font-medium text-text">{t('plans.day')} 1</span>
							<span class="opacity-60"> · </span>{plan.day_one.book_title}
						</p>
					{/if}
				</div>
			</ShelfCard>
		{/each}
	</div>
</div>
