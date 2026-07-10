<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';

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

<svelte:head><title>Set a new password — Ochorus</title></svelte:head>

<div class="mx-auto max-w-[26rem] px-5 py-12">
	{#if done}
		<div class="rounded-card border border-border bg-surface p-6 text-center">
			<h1 class="text-h2 mb-2">Password updated</h1>
			<p class="mb-4 text-body text-muted">You're all set — your new password is saved.</p>
			<a href={localizeHref('/')} class="btn btn-primary">Continue to Ochorus</a>
		</div>
	{:else if auth.user}
		<div class="mb-6 text-center">
			<h1 class="text-h1">Set a new password</h1>
			<p class="mt-1 text-small text-muted">Choose a new password for {auth.user.email}.</p>
		</div>
		<form class="rounded-card border border-border bg-surface p-6" onsubmit={submit}>
			<label class="mb-1 block text-small font-medium text-muted" for="password">New password</label>
			<input
				id="password"
				type="password"
				bind:value={password}
				autocomplete="new-password"
				required
				minlength="6"
				placeholder="••••••••"
				class="mb-3 w-full rounded-sm border border-border bg-bg px-3 py-2 text-body text-text"
			/>
			{#if error}<p class="mb-3 text-small text-danger">{error}</p>{/if}
			<button class="btn btn-primary w-full" type="submit" disabled={busy}>
				{busy ? '…' : 'Update password'}
			</button>
		</form>
	{:else}
		<div class="rounded-card border border-border bg-surface p-6 text-center">
			<h1 class="text-h2 mb-2">Reset link needed</h1>
			<p class="mb-4 text-body text-muted">
				This page opens from the password-reset link in your email. If the link has expired,
				request a new one.
			</p>
			<a href={localizeHref('/login')} class="btn btn-ghost">Back to sign in</a>
		</div>
	{/if}
</div>
