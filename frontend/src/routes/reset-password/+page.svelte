<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { authErrorKey } from '$lib/authErrors';

	const t = i18n.t;

	let password = $state('');
	let error = $state<string | null>(null);
	let busy = $state(false);
	let done = $state(false);
	let showPassword = $state(false);
	/** Measured — see the note on /login. */
	let revealW = $state(0);

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		busy = true;
		error = null;
		const err = await auth.updatePassword(password);
		busy = false;
		if (err) error = t(authErrorKey(err));
		else done = true;
	}
</script>

<svelte:head>
	<title>{t('reset.title')} — Ochorus</title>
	<!-- Same as /login: robots.txt Disallows this path, and this is the backstop
	     for a crawler that ignores it. -->
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="mx-auto max-w-[26rem] px-5 py-12">
	{#if done}
		<div class="rounded-card border border-border bg-surface p-6 text-center">
			<h1 class="text-h2 mb-2">{t('reset.updated')}</h1>
			<p class="mb-4 text-body text-muted">{t('reset.updatedBody')}</p>
			<a href={localizeHref('/')} class="btn btn-primary">{t('reset.continue')}</a>
		</div>
	{:else if auth.user}
		<div class="mb-6 text-center">
			<h1 class="text-h1">{t('reset.title')}</h1>
			<p class="mt-1 text-small text-muted">{t('reset.chooseFor')} {auth.user.email}.</p>
		</div>
		<form class="rounded-card border border-border bg-surface p-6" onsubmit={submit}>
			<label class="mb-1 block text-small font-medium text-muted" for="password">{t('reset.newPassword')}</label>
			<div class="pw-wrap mb-1" style="--reveal-w: {revealW}px">
				<input
					id="password"
					type={showPassword ? 'text' : 'password'}
					bind:value={password}
					autocomplete="new-password"
					required
					minlength="6"
					placeholder="••••••••"
					aria-invalid={error ? 'true' : undefined}
					aria-describedby="{error ? 'auth-error ' : ''}password-rule"
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
			<p id="password-rule" class="mb-3 text-micro text-muted">{t('login.passwordRule')}</p>
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
				disabled={busy}
				aria-busy={busy ? 'true' : undefined}
			>
				{#if busy}<span class="btn-spinner" aria-hidden="true"></span>{/if}
				{t('reset.updateBtn')}
			</button>
		</form>
	{:else}
		<div class="rounded-card border border-border bg-surface p-6 text-center">
			<h1 class="text-h2 mb-2">{t('reset.linkNeeded')}</h1>
			<p class="mb-4 text-body text-muted">{t('reset.linkNeededBody')}</p>
			<a href={localizeHref('/login')} class="btn btn-ghost">{t('reset.backToSignIn')}</a>
		</div>
	{/if}
</div>

<style>
	/* Mirrors /login's reveal — the same control on the same kind of field. */
	.pw-wrap {
		position: relative;
	}
	.pw-wrap .field {
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
