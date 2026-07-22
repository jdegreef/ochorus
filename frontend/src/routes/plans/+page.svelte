<script lang="ts">
	import type { PlanSummary } from '$lib/library';
	import { planProgress } from '$lib/planProgress.svelte';
	import { readingMinutes } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { SITE_URL } from '$lib/config';
	import { localizeHref, locales } from '$lib/paraglide/runtime';
	import CoverStrip from '$lib/components/CoverStrip.svelte';

	let { data } = $props();
	const plans = $derived<PlanSummary[]>(data.plans);
	const t = i18n.t;

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
	const canonical = `${SITE_URL}${localizeHref('/plans')}`;
	const alternates = locales.map((loc) => ({
		loc,
		href: `${SITE_URL}${localizeHref('/plans', { locale: loc })}`
	}));

	/** Rounded minutes of reading in an average day of a plan. */
	const perDay = (plan: PlanSummary) =>
		plan.day_count ? Math.max(1, readingMinutes(Math.round(plan.total_words / plan.day_count))) : 0;
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
</svelte:head>

<div class="mx-auto max-w-3xl px-5 py-10">
	<h1 class="text-h1 mb-2">{t('plans.title')}</h1>
	<p class="mb-8 max-w-xl text-body text-muted">{t('plans.tagline')}</p>

	{#if plans.length === 0}
		<p class="text-small text-muted">{t('plans.none')}</p>
	{/if}

	{#if showLengthFilter}
		<div class="mb-6 flex flex-wrap items-center gap-1.5" role="group" aria-label={t('plans.filterLength')}>
			<span class="mr-1 text-small text-muted">{t('plans.filterLength')}</span>
			{#each BUCKETS as b (b)}
				{#if b === 'all' || counts[b] > 0}
					<button
						type="button"
						class="rounded-full border px-2.5 py-1 text-[0.78rem]"
						class:border-accent={lengthFilter === b}
						class:bg-accent={lengthFilter === b}
						class:text-accent-contrast={lengthFilter === b}
						class:border-border={lengthFilter !== b}
						class:text-muted={lengthFilter !== b}
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

	<div class="space-y-4">
		{#each shownPlans as plan (plan.slug)}
			{@const done = planProgress.doneDays(plan.slug).length}
			{@const started = planProgress.isStarted(plan.slug)}
			<a
				href={localizeHref(`/plans/${plan.slug}`)}
				class="block rounded-card border border-border p-5 hover:bg-surface-2 hover:no-underline"
			>
				<div class="flex items-start justify-between gap-4">
					<div class="min-w-0 flex-1">
						<h2 class="text-h3 text-text">{plan.title}</h2>
						<p class="mt-0.5 text-small text-muted">
							{plan.day_count} {t('plans.days')}{#if plan.total_words}
								<span class="opacity-60"> · </span>~{perDay(plan)} {t('plans.minPerDay')}{/if}
						</p>
						<p class="mt-2 text-small text-muted">{plan.description}</p>
					</div>
					{#if plan.covers.length}
						<div class="hidden shrink-0 pt-1 sm:block">
							<CoverStrip covers={plan.covers} />
						</div>
					{/if}
				</div>
				{#if started}
					<div class="mt-3">
						<div class="h-1.5 overflow-hidden rounded-full bg-surface-2">
							<div
								class="h-full rounded-full bg-accent"
								style="width: {Math.round((done / plan.day_count) * 100)}%"
							></div>
						</div>
						<p class="mt-1.5 text-[0.78rem] text-muted">
							{done === plan.day_count
								? t('plans.finished')
								: `${t('plans.day')} ${planProgress.nextDay(plan.slug, plan.day_count)} ${t('plans.of')} ${plan.day_count}`}
						</p>
					</div>
				{/if}
			</a>
		{/each}
	</div>
</div>
