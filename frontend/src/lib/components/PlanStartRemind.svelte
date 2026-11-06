<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { planCalendarHref } from '$lib/planView';
	import { planSchedules } from '$lib/planSchedules.svelte';
	import { askForPlanEmail, planRemindTime, turnOffPlanEmail, turnOnPlanEmail } from '$lib/planEmail';
	import { seenOnView } from '$lib/signupSource';

	/**
	 * The daily reminder, offered at the moment of starting (design review #24):
	 * one quiet line under the plan page's Start button, never a sheet between
	 * the tap and day 1 (the 2026-10 UX audit took that out). Only what works
	 * today, on the web and in the app alike:
	 *   - signed in: the plan's own email switch and its time (planEmail — the
	 *     same opt-in the calendar view and PlanDayRemind set);
	 *   - signed out: the free-account ask that holds the choice until an
	 *     account exists (askForPlanEmail, counted as `plan_start`);
	 *   - either way, until the email is on: the calendar view, which makes the
	 *     Google / .ics reminders with no account at all.
	 * The end of each plan day still offers the email (PlanDayRemind) to a
	 * reader who passed it by here.
	 */
	let { slug }: { slug: string } = $props();

	const t = i18n.t;
	const prefs = $derived(planSchedules.get(slug));
	// A time picked here is the reader's; until then it follows the plan's own
	// (or Settings') reminder time, as PlanDayRemind's does.
	let picked = $state<string | null>(null);
	const time = $derived(picked ?? planRemindTime(slug));

	function setTime(value: string) {
		// A cleared input isn't a time; keep the last one.
		if (!value) return;
		picked = value;
		if (prefs.email) planSchedules.set(slug, { time: value });
	}
</script>

<div class="remind text-small" data-nosnippet>
	{#if auth.user}
		<label class="remind-switch">
			<input
				type="checkbox"
				checked={!!prefs.email}
				onchange={(e) => (e.currentTarget.checked ? turnOnPlanEmail(slug, time) : turnOffPlanEmail(slug))}
			/>
			<span class="font-medium text-text">{t('plans.remindEmail')}</span>
		</label>
		<input
			type="time"
			class="field remind-time"
			value={time}
			aria-label={t('plans.remindAt')}
			onchange={(e) => setTime(e.currentTarget.value)}
		/>
	{:else if auth.enabled}
		<button
			type="button"
			class="remind-link font-medium text-accent hover:underline"
			use:seenOnView={'plan_start'}
			onclick={() => askForPlanEmail(slug, 'plan_start', time)}>{t('plans.emailSignin')}</button
		>
	{/if}
	{#if !prefs.email}
		<a class="text-muted hover:text-text hover:underline" href={planCalendarHref(slug)}>{t('plans.remindCalendar')}</a>
	{/if}
</div>

<style>
	.remind {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.375rem 1rem;
	}
	.remind-switch {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
	}
	.remind-switch input {
		accent-color: var(--accent);
	}
	.remind-time {
		width: auto;
		padding-block: 0.25rem;
	}
	.remind-link {
		text-align: start;
	}
</style>
