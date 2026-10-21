<script lang="ts" module>
	/**
	 * The nudge's space, held before the app runs — ContinueReading's `hold`,
	 * for the row under the strip. Its frame and line boxes are the nudge's own
	 * below, with blank text; app.html's boot flag (`data-home-nudge`) says
	 * whether it shows, and which of its two variable rows it will draw: the
	 * streak figure or the no-streak line, the activity link or the button.
	 */
	export { hold };
</script>

<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
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

{#snippet hold()}
	<section class="rn-hold page-col px-5 pt-14" aria-hidden="true">
		<div
			class="flex flex-col gap-4 rounded-card border border-border bg-surface-2 px-5 py-4 sm:flex-row sm:items-center sm:gap-6"
		>
			<div class="flex items-center gap-3">
				<span class="h-[26px] w-[26px] skeleton rounded-full"></span>
				<div class="leading-tight">
					<div class="rn-if-streak">
						<span class="font-display text-h2 font-semibold">&nbsp;</span>
						<span class="ms-1 inline-block w-28 skeleton rounded text-body">&nbsp;</span>
					</div>
					<div class="rn-if-none w-36 skeleton rounded text-body">&nbsp;</div>
				</div>
			</div>
			<div class="hidden h-9 w-px bg-border sm:block"></div>
			<div class="min-w-0 flex-1">
				<div class="mb-1.5 text-small"><span class="inline-block w-32 skeleton rounded">&nbsp;</span></div>
				<div class="h-2 w-40 skeleton rounded-full"></div>
			</div>
			<span class="rn-if-today shrink-0 text-small font-semibold"
				><span class="inline-block w-24 skeleton rounded">&nbsp;</span></span
			>
			<span class="rn-if-open btn w-32 shrink-0 skeleton">&nbsp;</span>
		</div>
	</section>
{/snippet}

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
					{t('home.nudgeViewActivity')} <Arrow />
				</a>
			{:else}
				<a href={localizeHref('/books')} class="btn btn-primary shrink-0">
					{t('home.nudgeReadToday')}
				</a>
			{/if}
		</div>
	</section>
{/if}

<style>
	/* The hold draws what the boot flag says the nudge will (see `hold`). */
	:global(html:not([data-home-nudge])) .rn-hold,
	:global(html:not([data-home-nudge~='streak'])) .rn-if-streak,
	:global(html[data-home-nudge~='streak']) .rn-if-none,
	:global(html:not([data-home-nudge~='today'])) .rn-if-today,
	:global(html[data-home-nudge~='today']) .rn-if-open {
		display: none;
	}
</style>
