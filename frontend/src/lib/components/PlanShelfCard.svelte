<script lang="ts">
	import type { PlanSummary } from '$lib/library-public';
	import { planProgress } from '$lib/planProgress.svelte';
	import { readingMinutes } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { planMeta } from '$lib/emblemNames';
	import ShelfCard from '$lib/components/ShelfCard.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';

	/**
	 * One plan as a banded `<ShelfCard>` — the /plans shelf's card, and the plan
	 * page's "More like this" (so a related plan looks exactly as it does on the
	 * shelf). Not `PlanCard`: that is the compact resume row of "Your plans".
	 * Each plan wears its curated accent + emblem (planMeta); a started plan shows
	 * its progress (client-only, so the prerender bakes the "Day 1 · …" teaser).
	 */
	let { plan, headingLevel = 2 }: { plan: PlanSummary; headingLevel?: 2 | 3 } = $props();
	const t = i18n.t;
	// Looked up once per card, not per use: i18n.t is an uncached lookup.
	const OF = t('plans.of');
	const DAYS = t('plans.days');

	const meta = $derived(planMeta(plan.slug));
	const done = $derived(planProgress.doneDays(plan.slug).length);
	const started = $derived(planProgress.isStarted(plan.slug));
	/** Rounded minutes of reading in an average day of the plan. */
	const perDay = $derived(
		plan.day_count ? Math.max(1, readingMinutes(Math.round(plan.total_words / plan.day_count))) : 0
	);
	/** The progress bar's accessible name — the visible caption, in words. */
	const dayLabel = $derived(`${plan.title}: ${done} ${OF} ${plan.day_count} ${DAYS}`);
</script>

<ShelfCard
	href={localizeHref(`/plans/${plan.slug}`)}
	hue={meta.accent}
	emblem={meta.emblem}
	mark={{ top: DAYS, value: String(plan.day_count) }}
	covers={plan.covers}
	title={plan.title}
	{headingLevel}
>
	{#snippet aside()}
		{plan.day_count} {DAYS}{#if plan.total_words}
			<span class="opacity-60"> · </span>~{perDay} {t('plans.minPerDay')}{/if}
	{/snippet}
	<p class="shelf-card-desc mt-1.5 text-small text-muted">{plan.description}</p>
	<!-- Pushed to the bottom of the body so every card's footer sits on the
	     same line regardless of description length. -->
	<div class="mt-auto pt-3">
		{#if started}
			<ProgressBar percent={(done / plan.day_count) * 100} label={dayLabel} />
			<p class="mt-1.5 text-small text-muted">
				{done === plan.day_count
					? t('plans.finished')
					: `${t('plans.day')} ${planProgress.nextDay(plan.slug, plan.day_count)} ${OF} ${plan.day_count}`}
			</p>
		{:else if plan.day_one}
			<p class="text-small text-muted">
				<span class="font-medium text-text">{t('plans.day')} 1</span>
				<span class="opacity-60"> · </span>{plan.day_one.book_title || plan.day_one.chapter_title}
			</p>
		{/if}
	</div>
</ShelfCard>
