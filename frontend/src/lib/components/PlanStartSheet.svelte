<script lang="ts">
	import { goto } from '$app/navigation';
	import DrawerShell from '$lib/components/DrawerShell.svelte';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { planSchedules } from '$lib/planSchedules.svelte';
	import { signInSheet } from '$lib/signInSheet.svelte';
	import { promptSeen } from '$lib/signupSource';

	/**
	 * Asked once, right after a reader starts a plan: how should we remind you
	 * about day 2? Starting a plan is the clearest sign someone means to come
	 * back, so it's the moment to offer the reminder — and, signed out, the
	 * account that sends it (source plan_start).
	 *
	 * Nothing is pre-selected: daily email is something to choose, not a box
	 * to untick. Email saves the time and the email opt-in on the plan's
	 * schedule (synced to the account, which sends it: emails.plan_reminders).
	 * Signed out, the sign-up panel opens first, and the opt-in is saved only
	 * once an account exists — a reader who closes the panel has asked for
	 * nothing. Calendar hands over to the plan's calendar view, which already
	 * makes the Google / .ics reminders. Every path ends on day 1 except that.
	 */
	let {
		open = $bindable(false),
		slug,
		dayHref,
		onCalendar
	}: {
		open?: boolean;
		slug: string;
		/** Day 1's reader link. */
		dayHref: string;
		/** Switch the plan page to its calendar view. */
		onCalendar: () => void;
	} = $props();

	const t = i18n.t;
	const DEFAULT_TIME = '07:00';
	let choice = $state<'email' | 'calendar' | 'none' | null>(null);
	let time = $state(DEFAULT_TIME);
	const signedOut = $derived(auth.enabled && !auth.user);
	/** Waiting on the sign-up panel to turn on email reminders. */
	let pendingEmail = $state(false);

	$effect(() => {
		if (open && signedOut) promptSeen('plan_start');
	});

	const saveEmail = (at = time) =>
		planSchedules.set(slug, { ...planSchedules.get(slug), time: at || DEFAULT_TIME, email: true });

	// Google signs in by leaving the page and coming back to it, which loses
	// `pendingEmail`; the choice waits in this tab's sessionStorage instead and
	// is applied when the reader is back here signed in.
	const PENDING_KEY = 'ochorus:plan-email-pending';
	function rememberPending() {
		try {
			sessionStorage.setItem(PENDING_KEY, JSON.stringify({ slug, time }));
		} catch {
			/* storage blocked: the in-page path still works */
		}
	}
	$effect(() => {
		if (!auth.user) return;
		try {
			const raw = sessionStorage.getItem(PENDING_KEY);
			if (!raw) return;
			sessionStorage.removeItem(PENDING_KEY);
			const p = JSON.parse(raw) as { slug?: string; time?: string };
			if (p.slug === slug) saveEmail(p.time);
		} catch {
			/* nothing pending */
		}
	});

	// Signed out and chose email: once the panel closes, an account means the
	// opt-in is saved (and syncs up); no account means nothing was asked for.
	// Either way the reader goes on to day 1.
	$effect(() => {
		if (!pendingEmail || signInSheet.open) return;
		pendingEmail = false;
		try {
			sessionStorage.removeItem(PENDING_KEY);
		} catch {
			/* nothing to clear */
		}
		if (auth.user) saveEmail();
		goto(dayHref);
	});

	function go() {
		open = false;
		if (choice === 'calendar') {
			onCalendar();
			return;
		}
		if (choice === 'email') {
			if (signedOut) {
				rememberPending();
				// Next tick, after this sheet has let go of focus (as openFrom does).
				setTimeout(() => {
					pendingEmail = true;
					signInSheet.show('plan_start');
				}, 0);
				return;
			}
			saveEmail();
		}
		goto(dayHref);
	}
</script>

<DrawerShell bind:open title={t('plans.remindTitle')} placement="bottom">
	<div class="body">
		<p class="eyebrow">{t('plans.remindEyebrow')}</p>
		<fieldset class="opts">
			<legend class="sr-only">{t('plans.remindTitle')}</legend>
			<label class="opt" class:on={choice === 'email'}>
				<input type="radio" name="plan-remind" value="email" bind:group={choice} />
				<span><b>{t('plans.remindEmail')}</b><span class="hint">{t('plans.remindEmailHint')}</span></span>
			</label>
			{#if choice === 'email'}
				<label class="time">
					<span>{t('plans.remindAtShort')}</span>
					<input type="time" bind:value={time} class="field" />
				</label>
			{/if}
			<label class="opt" class:on={choice === 'calendar'}>
				<input type="radio" name="plan-remind" value="calendar" bind:group={choice} />
				<span><b>{t('plans.remindCalendar')}</b><span class="hint">{t('plans.remindCalendarHint')}</span></span>
			</label>
			<label class="opt" class:on={choice === 'none'}>
				<input type="radio" name="plan-remind" value="none" bind:group={choice} />
				<span><b>{t('plans.remindNone')}</b></span>
			</label>
		</fieldset>
		<button type="button" class="btn btn-primary w-full" onclick={go}>
			{choice === 'calendar' ? t('plans.remindCalendar') : t('plans.readDay1')}
		</button>
		{#if choice === 'email' && signedOut}
			<p class="hint text-center">{t('plans.remindAccount')}</p>
		{/if}
	</div>
</DrawerShell>

<style>
	.body {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		max-width: 26rem;
		width: 100%;
		margin-inline: auto;
	}
	.opts {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		border: 0;
		margin: 0;
		padding: 0;
	}
	.opt {
		display: flex;
		align-items: flex-start;
		gap: 0.6rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 0.7rem 0.8rem;
		cursor: pointer;
	}
	.opt.on {
		border-color: var(--accent);
		background: var(--accent-soft);
	}
	.opt input {
		margin-top: 0.2rem;
		accent-color: var(--accent);
	}
	.opt > span {
		display: flex;
		flex-direction: column;
	}
	.hint {
		font-size: var(--fs-small);
		color: var(--muted);
	}
	.time {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		padding-inline: 0.8rem;
		font-size: var(--fs-small);
		color: var(--muted);
	}
	.time .field {
		width: auto;
	}
</style>
