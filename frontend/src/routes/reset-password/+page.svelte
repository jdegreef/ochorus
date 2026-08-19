<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';

	const t = i18n.t;

	let password = $state('');
	let error = $state<string | null>(null);
	let busy = $state(false);
	let done = $state(false);

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		busy = true;
		error = null;
		const err = await auth.updatePassword(password);
		busy = false;
		if (err) error = err;
		else done = true;
	}
</script>

<svelte:head><title>{t('reset.title')} — Ochorus</title></svelte:head>

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
			<input
				id="password"
				type="password"
				bind:value={password}
				autocomplete="new-password"
				required
				minlength="6"
				placeholder="••••••••"
				aria-invalid={error ? 'true' : undefined}
				aria-describedby={error ? 'auth-error' : undefined}
				class="mb-3 w-full rounded-sm border border-border-strong bg-bg px-3 py-2 text-body text-text"
			/>
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
