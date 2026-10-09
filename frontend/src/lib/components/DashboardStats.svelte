<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
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
	import { currentStreak, longestStreak, localToday, streakTier } from '$lib/streak';
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
	const tier = $derived(streakTier(streak));
	// The flame grows with its tier: spark, flame, blaze, crown (streak.ts); the
	// halo, fill and crown ring are the `.streak-flame` rules in app.css.
	const flameSize = $derived({ spark: 28, flame: 30, blaze: 34, crown: 38 }[tier]);
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
		     a single "your reading" section. The panel carries the border and a
		     --surface ground (it sits on the home page's parchment band), and its
		     inner blocks are separated by hairlines rather than each floating. -->
		<div class="space-y-4 rounded-card border border-border bg-surface p-4 sm:p-5">
			<!-- Streak and weekly goal beside the reading calendar from lg up, so
			     the panel is one band rather than a tall stack; stacked below lg. -->
			<div class="grid gap-5 lg:grid-cols-[minmax(0,15rem)_minmax(0,1fr)] lg:items-center lg:gap-8">
				<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-6 lg:flex-col lg:items-stretch lg:gap-4">
					<div class="flex items-center gap-3">
						<span class="streak-flame" data-tier={tier}><Icon name="flame" size={flameSize} /></span>
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

					<div class="hidden h-9 w-px bg-border sm:block lg:hidden"></div>

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

				<!-- Reading calendar — a full year, stretched across its column. -->
				<div class="min-w-0">
					<h3 class="text-eyebrow mb-2 text-muted">{t('settings.heatmapTitle')}</h3>
					<ReadingHeatmap {days} {today} locale={lang.current} weeks={52} />
				</div>
			</div>

			<div class="h-px bg-border"></div>

			<!-- Totals, one slim line each -->
			<StatTiles stats={s} compact />

			<!-- Into the notebook, when there's something in it -->
			{#if hasNotebook}
				<a
					href={localizeHref('/notebook')}
					class="inline-flex items-center gap-1.5 text-small font-semibold text-accent hover:underline"
				>
					{t('notebook.title')} <Arrow />
				</a>
			{/if}
		</div>
	</section>
{/if}

