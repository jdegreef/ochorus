<script lang="ts">
	import { onMount } from 'svelte';
	import GoalPips from '$lib/components/GoalPips.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { lang } from '$lib/lang.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import ReadingHeatmap from '$lib/components/ReadingHeatmap.svelte';
	import StatTiles from '$lib/components/StatTiles.svelte';
	import { readingActivity } from '$lib/readingActivity.svelte';
	import { readingGoal } from '$lib/readingGoal.svelte';
	import { currentStreak, longestStreak, localToday } from '$lib/streak';
	import { weekReadCount } from '$lib/heatmap';
	import { readingCounts } from '$lib/readingStats';

	/**
	 * The signed-in dashboard's "your reading" panel: streak, weekly goal, a
	 * reading calendar, and totals. It gathers what the Settings › Activity view
	 * shows and brings it onto the home page, so a returning reader sees their
	 * momentum without hunting for it.
	 *
	 * Replaces the compact ReadingNudge on the dashboard (the marketing page
	 * keeps ReadingNudge for logged-out returning readers), so the streak isn't
	 * shown twice. Renders nothing until there's a day read — a brand-new reader
	 * gets the OnboardingCard instead. Client-only (prerendered page): read
	 * localStorage on mount and re-read on the ochorus:sync a sign-in merge fires.
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
	const longest = $derived(longestStreak(days));
	const weekCount = $derived(weekReadCount(days, today));
	const goal = $derived(readingGoal.perWeek);
	const goalMet = $derived(weekCount >= goal);

	// Every tile now comes straight from `readingCounts()` — "finished" is a
	// stored stamp, not a catalog lookup, so all six render at once (kept live by
	// `void ticks`, so an ochorus:sync merge or a finish refreshes them).
	const s = $derived.by(() => {
		void ticks;
		return readingCounts();
	});
	const hasNotebook = $derived(s.highlights + s.notes + s.bookmarks > 0);
</script>

{#if days.length}
	<section class="page-col px-5 pt-14">
		<!-- One panel, not three loose widgets: streak, totals and calendar read as
		     a single "your reading" section. The panel carries the border, so the
		     inner blocks sit on the page ground (surface-2 tiles keep their contrast
		     against it) and are separated by hairlines rather than each floating. -->
		<div class="space-y-5 rounded-card border border-border p-5 sm:p-6">
			<!-- Streak + weekly goal -->
			<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-6">
				<div class="flex items-center gap-3">
					<span class="text-gold"><Icon name="flame" size={28} /></span>
					<div class="leading-tight">
						{#if streak > 0}
							<div>
								<span class="font-display text-h2 font-semibold">{streak}</span>
								<span class="ms-1 text-body text-text">{t('settings.streakLabel')}</span>
							</div>
							<div class="text-small text-muted">
								{t('settings.streakLongest')}
								{longest}<span class="opacity-50"> · </span>{days.length}
								{t('settings.streakDaysRead')}
							</div>
						{:else}
							<div class="text-body text-text">{t('settings.streakNone')}</div>
						{/if}
					</div>
				</div>

				<div class="hidden h-9 w-px bg-border sm:block"></div>

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
			</div>

			<div class="h-px bg-border"></div>

			<!-- Totals -->
			<StatTiles stats={s} />

			<div class="h-px bg-border"></div>

			<!-- Reading calendar — a full year, stretched across the whole column. -->
			<div>
				<h3 class="text-h3 mb-2">{t('settings.heatmapTitle')}</h3>
				<ReadingHeatmap {days} {today} locale={lang.current} weeks={52} />
			</div>

			<!-- Into the notebook, when there's something in it -->
			{#if hasNotebook}
				<a
					href={localizeHref('/notebook')}
					class="inline-flex items-center gap-1.5 text-small font-semibold text-accent hover:underline"
				>
					{t('notebook.title')} →
				</a>
			{/if}
		</div>
	</section>
{/if}
