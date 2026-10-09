<script lang="ts">
	import type { Snippet } from 'svelte';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { planSchedules } from '$lib/planSchedules.svelte';
	import {
		declinePlanEmail,
		planEmailDeclined,
		planRemindTime,
		turnOffPlanEmail,
		turnOnPlanEmail
	} from '$lib/planEmail';

	/**
	 * The end of a plan day, for a SIGNED-IN reader whose plan doesn't email
	 * them yet: the plan's own email switch, the one its calendar view has,
	 * brought to where plan readers spend their time. That covers everyone who
	 * started before the plan-start question existed, chose "No reminder", or
	 * arrived on a day from a link. Ticking it turns the email on, and the ticked
	 * switch stays as the confirmation (and the way back off).
	 *
	 * Signed out, the end-of-chapter card (`otherwise`, ChapterEndAsk) makes
	 * this offer itself, with its own pacing, since it means an account. "Not
	 * now" stops this plan offering it. On the last day there's no tomorrow to
	 * send, so `otherwise` shows. Mount it keyed by day: what was done here
	 * belongs to this day's page.
	 */
	let {
		slug,
		day,
		dayCount,
		otherwise
	}: {
		slug: string;
		day: number;
		dayCount: number;
		/** What the end of the chapter shows when this card doesn't. */
		otherwise: Snippet;
	} = $props();

	const t = i18n.t;
	const prefs = $derived(planSchedules.get(slug));
	// What the input shows. A time the reader picks here is theirs; until then
	// it follows the plan (an account's time can arrive after this mounts, on
	// a fresh device), and switching on uses whatever is current at that moment.
	let picked = $state<string | null>(null);
	const time = $derived(picked ?? planRemindTime(slug));
	let declinedNow = $state(false);
	const declined = $derived(declinedNow || planEmailDeclined(slug));
	/** Switched on here: the card stays, as the switch, instead of vanishing. */
	let touched = $state(false);

	const offer = $derived(!!auth.user && day < dayCount && !declined && !prefs.email);

	function toggle(on: boolean) {
		touched = true;
		if (on) turnOnPlanEmail(slug, time);
		else turnOffPlanEmail(slug);
	}

	function setTime(value: string) {
		// A cleared input isn't a time; keep the last one.
		if (!value) return;
		picked = value;
		if (prefs.email) planSchedules.set(slug, { time: value });
	}

	function notNow() {
		declinePlanEmail(slug);
		declinedNow = true;
	}
</script>

{#if !declined && (offer || (touched && auth.user))}
	<aside class="ask" aria-label={t('plans.emailToggle')} data-nosnippet>
		<label class="email-toggle">
			<input type="checkbox" checked={!!prefs.email} onchange={(e) => toggle(e.currentTarget.checked)} />
			<span>
				<span class="text-small font-semibold text-text">{t('plans.emailToggle')}</span>
				<span class="block text-micro text-muted">{t('plans.emailToggleHint')}</span>
			</span>
		</label>
		<div class="ask-row">
			<label class="time text-small text-muted">
				<span>{t('plans.remindAt')}</span>
				<input type="time" value={time} onchange={(e) => setTime(e.currentTarget.value)} class="field" />
			</label>
			{#if !prefs.email}
				<button type="button" class="btn btn-ghost btn-sm" onclick={notNow}>{t('reader.askLater')}</button>
			{/if}
		</div>
	</aside>
{:else}
	{@render otherwise()}
{/if}

<style>
	/* The end-of-chapter card's shape (ChapterEndAsk), so the two read as one. */
	.ask {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
		margin-top: 1.5rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		padding: 1rem 1.1rem;
		text-align: start;
	}
	.email-toggle {
		display: flex;
		align-items: flex-start;
		gap: 0.6rem;
		cursor: pointer;
	}
	.email-toggle input {
		margin-top: 0.2rem;
		accent-color: var(--accent);
	}
	.ask-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
	}
	.time {
		display: flex;
		align-items: center;
		gap: 0.6rem;
	}
	.time .field {
		width: auto;
	}
</style>
