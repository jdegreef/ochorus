<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { authErrorKey } from '$lib/authErrors';
	import { signupStarted } from '$lib/signupSource';
	import GoogleButton from '$lib/components/GoogleButton.svelte';

	/**
	 * Create an account in the sign-up panel (SignInSheet): Google, or an email
	 * and a password — the same Supabase sign-up as /login's create-account form.
	 *
	 * A signed-in session ends the flow (the panel closes itself). When the
	 * project asks for email confirmation there is no session yet, so the form
	 * says where the confirmation link went; that link brings the reader back
	 * to `returnTo`.
	 */
	let {
		email = $bindable(''),
		returnTo,
		onSignIn
	}: {
		email?: string;
		/** The page the confirmation link or Google returns to (default: the home page). */
		returnTo?: string;
		/** "Already have an account? Sign in" — omitted, the link isn't shown. */
		onSignIn?: () => void;
	} = $props();

	const t = i18n.t;
	const uid = $props.id();

	let password = $state('');
	let showPassword = $state(false);
	/** Measured, because the label is translated — "Показати" is twice "Show". */
	let revealW = $state(0);
	let busy = $state(false);
	let error = $state<string | null>(null);
	let sent = $state(false);
	// One "Signup started" per reader, not one per retry after an error.
	let started = false;
	let resendIn = $state(0);
	let resent = $state<string | null>(null);

	// 30s between sends, as on /login: hammering Resend trips Supabase's rate
	// limit, which then blocks the send that would have worked.
	const RESEND_WAIT = 30;
	let tick: ReturnType<typeof setInterval> | undefined;
	$effect(() => () => clearInterval(tick));

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		busy = true;
		error = null;
		if (!started) signupStarted();
		started = true;
		const err = await auth.signUp(email, password, returnTo);
		busy = false;
		if (err) {
			error = t(authErrorKey(err));
			return;
		}
		password = '';
		// Signed in already (no email confirmation): the panel closes itself, and
		// no link was sent to tell the reader about.
		if (!auth.user) sent = true;
	}

	async function resend() {
		if (resendIn > 0) return;
		resent = null;
		resendIn = RESEND_WAIT;
		clearInterval(tick);
		tick = setInterval(() => {
			resendIn -= 1;
			if (resendIn <= 0) clearInterval(tick);
		}, 1000);
		const err = await auth.resendSignup(email, returnTo);
		resent = err ? t(authErrorKey(err)) : t('login.sentAgain');
	}

	async function google() {
		busy = true;
		error = null;
		if (!started) signupStarted();
		started = true;
		const err = await auth.signInWithGoogle(returnTo);
		// On success the browser navigates to Google; only reachable on error.
		if (err) {
			error = t(authErrorKey(err));
			busy = false;
		}
	}
</script>

{#if sent}
	<div class="suf">
		<h3 class="text-h3">{t('login.checkEmail')}</h3>
		<p class="text-body text-muted">{t('login.sentSignup').replace('%email%', email)}</p>
		<p class="text-center text-small text-muted">
			{t('login.didntGet')}
			<button type="button" class="text-accent" onclick={resend} disabled={resendIn > 0}>
				{resendIn > 0 ? t('login.resendIn').replace('%n%', String(resendIn)) : t('login.resend')}
			</button>
		</p>
		<p role="status" class="text-center text-small text-muted">{resent ?? ''}</p>
	</div>
{:else}
	<form class="suf" onsubmit={submit}>
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
		<label class="text-small font-medium text-muted" for="{uid}-password">{t('login.password')}</label>
		<div class="pw-wrap" style="--reveal-w: {revealW}px">
			<input
				id="{uid}-password"
				type={showPassword ? 'text' : 'password'}
				bind:value={password}
				autocomplete="new-password"
				required
				minlength="6"
				placeholder="••••••••"
				aria-invalid={error ? 'true' : undefined}
				aria-describedby="{uid}-err {uid}-rule"
				class="field w-full"
			/>
			<button
				bind:clientWidth={revealW}
				type="button"
				class="pw-toggle"
				onclick={() => (showPassword = !showPassword)}
				aria-pressed={showPassword}
			>
				{showPassword ? t('login.hidePassword') : t('login.showPassword')}
			</button>
		</div>
		<p id="{uid}-rule" class="text-micro text-muted">{t('login.passwordRule')}</p>
		<p id="{uid}-err" role="alert" class="text-small text-danger">{error ?? ''}</p>
		<button class="btn btn-primary w-full" type="submit" disabled={busy || !auth.enabled} aria-busy={busy ? 'true' : undefined}>
			{#if busy}<span class="btn-spinner" aria-hidden="true"></span>{/if}
			{t('login.createAccountBtn')}
		</button>
		{#if onSignIn}
			<p class="text-center text-small text-muted">
				{t('login.haveAccount')}
				<button type="button" class="text-accent" onclick={onSignIn}>{t('account.signIn')}</button>
			</p>
		{/if}
	</form>
{/if}

<style>
	.suf {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}
	/* Collapsed, not display:none: a live region (the error, "sent again") is
	   only announced if it was already in the accessibility tree when its text
	   arrived. The negative margin takes back the flex gap it would leave. */
	.suf p:empty {
		margin-block-end: -0.6rem;
	}
	.pw-wrap {
		position: relative;
	}
	.pw-wrap .field {
		/* Measured rather than a fixed 4.5rem: the label is translated, and the
		   Ukrainian and Swahili words are wide enough to sit on top of the dots. */
		padding-inline-end: calc(var(--reveal-w, 3rem) + 1.1rem);
	}
	.pw-toggle {
		position: absolute;
		inset-inline-end: 0.6rem;
		top: 50%;
		transform: translateY(-50%);
		font-size: var(--fs-small);
		font-weight: 600;
		color: var(--accent);
		background: none;
		border: 0;
		cursor: pointer;
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
