<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { authErrorKey } from '$lib/authErrors';
	import { inboxFor } from '$lib/inbox';
	import { signupStarted } from '$lib/signupSource';
	import GoogleButton from '$lib/components/GoogleButton.svelte';

	/**
	 * Passwordless sign-up / sign-in: Google, or an email that receives a link
	 * AND a 6-digit code (one Supabase OTP email). The code is the point — it
	 * works when the email is opened on another device, or in a mail app whose
	 * own browser would lose the session a link opens.
	 *
	 * Used by the sign-up panel over any page (SignInSheet) and by /login, so the
	 * two can't drift. A signed-in session ends the flow: the parent closes the
	 * panel or routes on, as it does for any sign-in.
	 */
	let {
		email = $bindable(''),
		cta,
		counts = true,
		returnTo,
		onPassword
	}: {
		email?: string;
		/** The send button's words; defaults to "Email me a sign-in code". */
		cta?: string;
		/** Count a send / Google press as a sign-up start (false for sign-in). */
		counts?: boolean;
		/** The page an emailed link or Google returns to (default: the home page). */
		returnTo?: string;
		/** "Use a password instead" — omitted, the link isn't shown. */
		onPassword?: () => void;
	} = $props();

	const t = i18n.t;
	const uid = $props.id();

	let step = $state<'email' | 'code'>('email');
	let code = $state('');
	let busy = $state(false);
	let error = $state<string | null>(null);
	let resendIn = $state(0);
	let resent = $state(false);
	const inbox = $derived(inboxFor(email));

	const RESEND_WAIT = 30;
	let tick: ReturnType<typeof setInterval> | undefined;
	function startWait() {
		clearInterval(tick);
		resendIn = RESEND_WAIT;
		tick = setInterval(() => {
			resendIn -= 1;
			if (resendIn <= 0) clearInterval(tick);
		}, 1000);
	}
	$effect(() => () => clearInterval(tick));

	async function send(e?: SubmitEvent) {
		e?.preventDefault();
		if (!email) {
			error = t('login.enterEmailFirst');
			return;
		}
		busy = true;
		error = null;
		if (counts && step === 'email') signupStarted();
		const err = await auth.signInWithMagicLink(email, returnTo);
		busy = false;
		if (err) {
			error = t(authErrorKey(err));
			return;
		}
		resent = step === 'code';
		step = 'code';
		startWait();
	}

	async function verify(e: SubmitEvent) {
		e.preventDefault();
		const digits = code.replace(/\D/g, '');
		if (digits.length !== 6) {
			error = t('authErr.codeInvalid');
			return;
		}
		busy = true;
		error = null;
		const err = await auth.verifyEmailCode(email, digits);
		busy = false;
		if (err) error = t(authErrorKey(err));
	}

	async function google() {
		busy = true;
		error = null;
		if (counts) signupStarted();
		const err = await auth.signInWithGoogle(returnTo);
		// On success the browser navigates to Google; only reachable on error.
		if (err) {
			error = t(authErrorKey(err));
			busy = false;
		}
	}
</script>

{#if step === 'email'}
	<form class="ecf" onsubmit={send}>
		<GoogleButton onclick={google} disabled={busy || !auth.enabled} />
		<div class="or-divider text-small text-muted" aria-hidden="true">{t('login.or')}</div>
		<label class="text-small font-medium text-muted" for="{uid}-email">{t('login.email')}</label>
		<input
			id="{uid}-email"
			type="email"
			bind:value={email}
			autocomplete="email"
			required
			placeholder="you@example.com"
			aria-invalid={error ? 'true' : undefined}
			aria-describedby="{uid}-err"
			class="field w-full"
		/>
		<p id="{uid}-err" role="alert" class="text-small text-danger">{error ?? ''}</p>
		<button class="btn btn-primary w-full" type="submit" disabled={busy || !auth.enabled} aria-busy={busy ? 'true' : undefined}>
			{#if busy}<span class="btn-spinner" aria-hidden="true"></span>{/if}
			{cta ?? t('login.emailCode')}
		</button>
		{#if onPassword}
			<button type="button" class="text-small text-accent" onclick={onPassword}>{t('login.usePassword')}</button>
		{/if}
		<p class="text-center text-micro text-muted">{t('login.noPassword')}</p>
	</form>
{:else}
	<form class="ecf" onsubmit={verify}>
		<p class="text-body">{t('login.codeSent').replace('%email%', email)}</p>
		<label class="text-small font-medium text-muted" for="{uid}-code">{t('login.codeLabel')}</label>
		<input
			id="{uid}-code"
			bind:value={code}
			inputmode="numeric"
			autocomplete="one-time-code"
			maxlength="7"
			pattern="[0-9 ]*"
			placeholder="123456"
			aria-invalid={error ? 'true' : undefined}
			aria-describedby="{uid}-err"
			class="field code w-full"
		/>
		<p id="{uid}-err" role="alert" class="text-small text-danger">{error ?? ''}</p>
		<button class="btn btn-primary w-full" type="submit" disabled={busy} aria-busy={busy ? 'true' : undefined}>
			{#if busy}<span class="btn-spinner" aria-hidden="true"></span>{/if}
			{t('login.verify')}
		</button>
		{#if inbox}
			<a class="btn btn-ghost w-full" href={inbox.url} target="_blank" rel="noopener noreferrer"
				>{t('login.openInbox').replace('%name%', inbox.name)}</a
			>
		{/if}
		<p class="text-center text-small text-muted">
			{t('login.didntGet')}
			<button type="button" class="text-accent" onclick={() => send()} disabled={resendIn > 0 || busy}>
				{resendIn > 0 ? t('login.resendIn').replace('%n%', String(resendIn)) : t('login.resend')}
			</button>
		</p>
		{#if resent}<p role="status" class="text-center text-small text-muted">{t('login.sentAgain')}</p>{/if}
		<button
			type="button"
			class="text-small text-accent"
			onclick={() => {
				step = 'email';
				code = '';
				error = null;
			}}>{t('login.changeEmail')}</button
		>
	</form>
{/if}

<style>
	.ecf {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}
	.ecf p:empty {
		display: none;
	}
	.code {
		font-size: var(--fs-h3);
		letter-spacing: 0.4em;
		text-align: center;
		font-variant-numeric: tabular-nums;
	}
	.or-divider {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.or-divider::before,
	.or-divider::after {
		content: '';
		flex: 1;
		height: 1px;
		background: var(--border);
	}
</style>
