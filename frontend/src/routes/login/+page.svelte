<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { authErrorKey } from '$lib/authErrors';
	import BrandMark from '$lib/components/BrandMark.svelte';
	import GoogleMark from '$lib/components/GoogleMark.svelte';

	const t = i18n.t;

	type Mode = 'signin' | 'signup' | 'reset';

	// Mode lives in the URL (?mode=signup / reset), so each form is a real place:
	// linkable, bookmarkable, and Back steps between them instead of leaving the
	// page entirely. It was component state, which also meant the tab title said
	// "Sign in" over a "Create your account" heading.
	const MODES: Mode[] = ['signin', 'signup', 'reset'];
	const mode = $derived<Mode>(
		(MODES as string[]).includes($page.url.searchParams.get('mode') ?? '')
			? ($page.url.searchParams.get('mode') as Mode)
			: 'signin'
	);
	let email = $state('');
	let password = $state('');
	let error = $state<string | null>(null);
	let busy = $state(false);
	// Which confirmation card to show after an email is dispatched.
	let sent = $state<null | 'magic' | 'signup' | 'reset'>(null);
	let resentMsg = $state<string | null>(null);
	let resentErr = $state<string | null>(null);
	/** Seconds until Resend is allowed again — the button had no throttle at all. */
	let resendIn = $state(0);
	let showPassword = $state(false);
	/** Measured, because the label is translated — "Показати" is twice "Show". */
	let revealW = $state(0);
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

	// Clearing on the MODE, not in the click handler: mode now comes from the
	// URL, so Back and Forward change the form without any handler running. A
	// "that email and password don't match" from the sign-in form would
	// otherwise still be sitting (with aria-invalid) over the reset form.
	let lastMode: Mode | null = null;
	$effect(() => {
		if (lastMode !== null && mode !== lastMode) error = null;
		lastMode = mode;
	});

	function switchMode(m: Mode) {
		const url = new URL($page.url);
		if (m === 'signin') url.searchParams.delete('mode');
		else url.searchParams.set('mode', m);
		// pushState, not replace: switching form IS a navigation the reader can undo.
		goto(url, { keepFocus: true, noScroll: true });
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
		if (err) error = t(authErrorKey(err));
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
		if (err) error = t(authErrorKey(err));
		else sent = 'magic';
	}

	async function google() {
		busy = true;
		error = null;
		const err = await auth.signInWithGoogle();
		// On success the browser navigates to Google; only reachable on error.
		if (err) {
			error = t(authErrorKey(err));
			busy = false;
		}
	}

	// 30s between sends. Without this the button was tappable as fast as a finger
	// moves, and the only thing stopping a reader from hammering their own inbox
	// (and tripping Supabase's rate limit, which then blocks the send that would
	// have worked) was politeness.
	const RESEND_WAIT = 30;

	async function resend() {
		if (resendIn > 0) return;
		resentMsg = null;
		resentErr = null;
		resendIn = RESEND_WAIT;
		const tick = setInterval(() => {
			resendIn -= 1;
			if (resendIn <= 0) clearInterval(tick);
		}, 1000);
		const err =
			sent === 'reset' ? await auth.sendPasswordReset(email) : await auth.signInWithMagicLink(email);
		if (err) resentErr = t(authErrorKey(err));
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

<svelte:head>
	<title>{titles[mode]} — Ochorus</title>
	<!-- Belt and braces. robots.txt already Disallows /login, which is what
	     actually keeps crawlers off it — and note the two do not compose: a
	     disallowed page is never fetched, so this tag is never READ. It is here
	     for the case where the Disallow is relaxed (to spend crawl budget
	     elsewhere) and for crawlers that ignore robots.txt entirely. -->
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="mx-auto max-w-[26rem] px-5 py-12">
	{#if sent}
		<!-- Email dispatched: confirmation card -->
		<div class="rounded-card border border-border bg-surface p-6 text-center">
			<div class="mail-badge mx-auto mb-3">✉</div>
			<h1 class="text-h2 mb-2">{t('login.checkEmail')}</h1>
			<p class="mb-4 text-body text-muted">{sentBody}</p>
			<div class="border-t border-border pt-4">
				<p class="mb-2 text-small text-muted">{t('login.didntGet')}</p>
				<button class="btn btn-ghost" onclick={resend} disabled={resendIn > 0}>
					{resendIn > 0 ? t('login.resendIn').replace('%n%', String(resendIn)) : t('login.resend')}
				</button>
				{#if resentMsg}<p role="status" class="mt-2 text-small text-muted">{resentMsg}</p>{/if}
				{#if resentErr}<p role="alert" class="mt-2 text-small text-danger">{resentErr}</p>{/if}
			</div>
		</div>
		<p class="mt-4 text-center text-small">
			<a href={localizeHref('/login')} onclick={() => (sent = null)} class="text-accent">← {t('login.backToSignIn')}</a>
		</p>
	{:else}
		<div class="mb-6 text-center">
			<!-- The lockup every other surface uses. A ❦ here made the one screen
			     asking for a password the one screen not wearing the brand. -->
			<div class="mx-auto mb-3 flex justify-center text-accent"><BrandMark height={40} /></div>
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
				<div class="pw-wrap mb-1" style="--reveal-w: {revealW}px">
					<input
						id="password"
						type={showPassword ? 'text' : 'password'}
						bind:value={password}
						autocomplete={mode === 'signin' ? 'current-password' : 'new-password'}
						required
						minlength="6"
						placeholder="••••••••"
						aria-invalid={error ? 'true' : undefined}
						aria-describedby="{error ? 'auth-error ' : ''}password-rule"
						class="field w-full"
					/>
					<!-- A reveal, because the alternative on a phone keyboard is typing a
					     password you cannot see and finding out only after it fails. -->
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
				<!-- Stated up front, not discovered when the browser rejects the form. -->
				<p id="password-rule" class="mb-3 text-micro text-muted">{t('login.passwordRule')}</p>
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
					<GoogleMark />
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

	/* The reveal sits inside the field's box rather than beside it, so the input
	   keeps the full row width the other fields have. */
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
</style>
