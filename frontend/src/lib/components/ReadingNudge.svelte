<script lang="ts">
	import { onMount } from 'svelte';
	import GoalPips from '$lib/components/GoalPips.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import Icon from '$lib/components/Icon.svelte';
	import { readingActivity } from '$lib/readingActivity.svelte';
	import { readingGoal } from '$lib/readingGoal.svelte';
	import { currentStreak, localToday } from '$lib/streak';
	import { weekReadCount } from '$lib/heatmap';

	/**
	 * A compact streak + weekly-goal nudge for the home dashboard. Reads the same
	 * synced activity log the streak/heatmap use (readingActivity). Renders
	 * nothing until there's activity — a brand-new visitor sees the library lead,
	 * not an empty target. Client-only: this page is prerendered, so localStorage
	 * is read on mount (and re-read on the ochorus:sync event a sign-in merge
	 * fires), mirroring ContinueReading.
	 */
	const t = i18n.t;

	let ticks = $state(0);
	onMount(() => {
		const bump = () => ticks++;
		bump();
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	const days = $derived.by(() => {
		void ticks;
		return readingActivity.days();
	});
	const today = $derived(localToday());
	const streak = $derived(currentStreak(days, today));
	const weekCount = $derived(weekReadCount(days, today));
	const goal = $derived(readingGoal.perWeek);
	const goalMet = $derived(weekCount >= goal);
	const readToday = $derived(days.includes(today));
</script>

{#if days.length}
	<section class="page-col px-5 pt-14">
		<div
			class="flex flex-col gap-4 rounded-card border border-border bg-surface-2 px-5 py-4 sm:flex-row sm:items-center sm:gap-6"
		>
			<!-- Streak -->
			<div class="flex items-center gap-3">
				<span class="text-gold"><Icon name="flame" size={26} /></span>
				<div class="leading-tight">
					{#if streak > 0}
						<div>
							<span class="font-display text-h2 font-semibold">{streak}</span>
							<span class="ms-1 text-body text-text">{t('settings.streakLabel')}</span>
						</div>
					{:else}
						<div class="text-body text-text">{t('settings.streakNone')}</div>
					{/if}
				</div>
			</div>

			<div class="hidden h-9 w-px bg-border sm:block"></div>

			<!-- Weekly goal -->
			<div class="min-w-0 flex-1">
				<div class="mb-1.5 text-small text-muted">
					{#if goalMet}
						{t('settings.goalMet')}
					{:else}
						{weekCount} {t('settings.goalOf')} {goal} {t('settings.goalDaysThisWeek')}
					{/if}
				</div>
				<GoalPips {goal} {weekCount} />
			</div>

			<!-- CTA: prompt reading when today is still open, else link to the calendar -->
			{#if readToday}
				<a
					href="{localizeHref('/settings')}?section=activity"
					class="shrink-0 text-small font-semibold text-accent hover:underline"
				>
					{t('home.nudgeViewActivity')} →
				</a>
			{:else}
				<a href={localizeHref('/books')} class="btn btn-primary shrink-0">
					{t('home.nudgeReadToday')}
				</a>
			{/if}
		</div>
	</section>
{/if}
