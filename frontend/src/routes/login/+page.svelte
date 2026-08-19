<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';

	const t = i18n.t;

	type Mode = 'signin' | 'signup' | 'reset';

	let mode = $state<Mode>('signin');
	let email = $state('');
	let password = $state('');
	let error = $state<string | null>(null);
	let busy = $state(false);
	// Which confirmation card to show after an email is dispatched.
	let sent = $state<null | 'magic' | 'signup' | 'reset'>(null);
	let resentMsg = $state<string | null>(null);
	let resentErr = $state<string | null>(null);
	let routed = false;

	// The redirect param is captured from the (already locale-prefixed) URL, so
	// it needs no re-localizing; only the fallback home does.
	const redirectTarget = $derived($page.url.searchParams.get('redirect') || localizeHref('/'));

	// Once a session exists (password sign-in, or returning from a magic/OAuth
	// redirect), leave the login page for wherever the user was headed.
	$effect(() => {
		if (auth.user && !routed) {
			routed = true;
			goto(redirectTarget);
		}
	});

	const titles = $derived<Record<Mode, string>>({
		signin: t('login.welcomeBack'),
		signup: t('login.signupTitle'),
		reset: t('login.resetTitle')
	});

	function switchMode(m: Mode) {
		mode = m;
		error = null;
	}

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		busy = true;
		error = null;
		let err: string | null;
		if (mode === 'reset') {
			err = await auth.sendPasswordReset(email);
			if (!err) sent = 'reset';
		} else if (mode === 'signup') {
			err = await auth.signUp(email, password);
			if (!err) sent = 'signup';
		} else {
			err = await auth.signIn(email, password);
			// success routes via the $effect above
		}
		busy = false;
		if (err) error = err;
		else password = '';
	}

	async function magicLink() {
		if (!email) {
			error = t('login.enterEmailFirst');
			return;
		}
		busy = true;
		error = null;
		const err = await auth.signInWithMagicLink(email);
		busy = false;
		if (err) error = err;
		else sent = 'magic';
	}

	async function google() {
		busy = true;
		error = null;
		const err = await auth.signInWithGoogle();
		// On success the browser navigates to Google; only reachable on error.
		if (err) {
			error = err;
			busy = false;
		}
	}

	async function resend() {
		resentMsg = null;
		resentErr = null;
		const err =
			sent === 'reset' ? await auth.sendPasswordReset(email) : await auth.signInWithMagicLink(email);
		if (err) resentErr = err;
		else resentMsg = t('login.sentAgain');
	}

	const sentBody = $derived(
		(sent === 'signup'
			? t('login.sentSignup')
			: sent === 'reset'
				? t('login.sentReset')
				: t('login.sentMagic')
		).replace('%email%', email)
	);
</script>

<svelte:head><title>{t('account.signIn')} — Ochorus</title></svelte:head>

<div class="mx-auto max-w-[26rem] px-5 py-12">
	{#if sent}
		<!-- Email dispatched: confirmation card -->
		<div class="rounded-card border border-border bg-surface p-6 text-center">
			<div class="mail-badge mx-auto mb-3">✉</div>
			<h1 class="text-h2 mb-2">{t('login.checkEmail')}</h1>
			<p class="mb-4 text-body text-muted">{sentBody}</p>
			<div class="border-t border-border pt-4">
				<p class="mb-2 text-small text-muted">{t('login.didntGet')}</p>
				<button class="btn btn-ghost" onclick={resend}>{t('login.resend')}</button>
				{#if resentMsg}<p role="status" class="mt-2 text-small text-muted">{resentMsg}</p>{/if}
				{#if resentErr}<p role="alert" class="mt-2 text-small text-danger">{resentErr}</p>{/if}
			</div>
		</div>
		<p class="mt-4 text-center text-small">
			<a href={localizeHref('/login')} onclick={() => (sent = null)} class="text-accent">← {t('login.backToSignIn')}</a>
		</p>
	{:else}
		<div class="mb-6 text-center">
			<div class="brand-mark mx-auto mb-3">❦</div>
			<h1 class="text-h1">{titles[mode]}</h1>
			<p class="mt-1 text-small text-muted">
				{t('login.syncNote')}
			</p>
		</div>

		<form class="rounded-card border border-border bg-surface p-6" onsubmit={submit}>
			<label class="mb-1 block text-small font-medium text-muted" for="email">{t('login.email')}</label>
			<input
				id="email"
				type="email"
				bind:value={email}
				autocomplete="email"
				required
				placeholder="you@example.com"
				aria-invalid={error ? 'true' : undefined}
				aria-describedby={error ? 'auth-error' : undefined}
				class="field mb-3 w-full"
			/>

			{#if mode !== 'reset'}
				<label class="mb-1 block text-small font-medium text-muted" for="password">{t('login.password')}</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					autocomplete={mode === 'signin' ? 'current-password' : 'new-password'}
					required
					minlength="6"
					placeholder="••••••••"
					aria-invalid={error ? 'true' : undefined}
					aria-describedby={error ? 'auth-error' : undefined}
					class="field mb-3 w-full"
				/>
			{/if}

			<!-- Rendered unconditionally, empty and zero-height when there is nothing
			     to say: a live region is only announced if it was already in the DOM
			     when its text arrived, so inserting the <p> together with the message
			     is the classic way to ship an error no screen reader ever reads out. -->
			<p id="auth-error" role="alert" class="text-small text-danger {error ? 'mb-3' : ''}">
				{error ?? ''}
			</p>

			<button
				class="btn btn-primary w-full"
				type="submit"
				disabled={busy || !auth.enabled}
				aria-busy={busy ? 'true' : undefined}
			>
				{#if busy}<span class="btn-spinner" aria-hidden="true"></span>{/if}
				{mode === 'signin'
					? t('account.signIn')
					: mode === 'signup'
						? t('login.createAccountBtn')
						: t('login.sendReset')}
			</button>

			{#if mode !== 'reset'}
				<button
					class="btn btn-ghost mt-2 w-full"
					type="button"
					onclick={magicLink}
					disabled={busy || !auth.enabled}
				>
					{t('login.magicLink')}
				</button>

				<div class="or-divider text-small text-muted" aria-hidden="true">{t('login.or')}</div>

				<button
					class="google-btn"
					type="button"
					onclick={google}
					disabled={busy || !auth.enabled}
				>
					<svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
						<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
						<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
						<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
						<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
					</svg>
					{t('login.google')}
				</button>
			{/if}

			{#if mode === 'signin'}
				<p class="mt-4 mb-0 text-center text-small">
					<button type="button" class="text-accent" onclick={() => switchMode('reset')}>
						{t('login.forgot')}
					</button>
				</p>
			{/if}
		</form>

		<p class="mt-4 text-center text-small text-muted">
			{#if mode === 'signin'}
				{t('login.newTo')}
				<button type="button" class="text-accent" onclick={() => switchMode('signup')}>{t('login.createAccountLink')}</button>
			{:else if mode === 'signup'}
				{t('login.haveAccount')}
				<button type="button" class="text-accent" onclick={() => switchMode('signin')}>{t('account.signIn')}</button>
			{:else}
				<button type="button" class="text-accent" onclick={() => switchMode('signin')}>← {t('login.backToSignIn')}</button>
			{/if}
		</p>

		{#if !auth.enabled}
			<p class="mt-4 text-center text-small text-muted">
				{t('login.accountsDisabled')}
			</p>
		{/if}
	{/if}
</div>

<style>
	.brand-mark,
	.mail-badge {
		display: flex;
		height: 3.25rem;
		width: 3.25rem;
		align-items: center;
		justify-content: center;
		border-radius: 999px;
		font-family: var(--font-display);
		font-size: var(--fs-h2);
		color: var(--accent);
		background: color-mix(in srgb, var(--accent) 14%, transparent);
	}
	.mail-badge {
		color: var(--gold);
		background: color-mix(in srgb, var(--gold) 16%, transparent);
	}
	.or-divider {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin: 1rem 0;
	}
	.or-divider::before,
	.or-divider::after {
		content: '';
		flex: 1;
		height: 1px;
		background: var(--border);
	}
	.google-btn {
		display: flex;
		width: 100%;
		align-items: center;
		justify-content: center;
		gap: 0.6rem;
		padding: 0.6rem 1.1rem;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		background: var(--surface-2);
		color: var(--text);
		font-family: var(--font-sans);
		font-weight: 600;
		font-size: var(--fs-body);
		cursor: pointer;
		transition: background var(--duration-fast) ease, border-color var(--duration-fast) ease;
	}
	.google-btn:hover:not(:disabled) {
		background: var(--surface);
		border-color: var(--accent-soft-border);
	}
	.google-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}
</style>
