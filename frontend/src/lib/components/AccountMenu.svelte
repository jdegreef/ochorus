<script lang="ts">
	import { auth } from '$lib/auth.svelte';

	let open = $state(false);
	let mode = $state<'in' | 'up'>('in');
	let email = $state('');
	let password = $state('');
	let error = $state<string | null>(null);
	let busy = $state(false);
	let notice = $state<string | null>(null);

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		busy = true;
		error = null;
		notice = null;
		const fn = mode === 'in' ? auth.signIn(email, password) : auth.signUp(email, password);
		const err = await fn;
		busy = false;
		if (err) {
			error = err;
			return;
		}
		if (mode === 'up') {
			notice = 'Check your email to confirm your account.';
		} else {
			open = false;
		}
		password = '';
	}
</script>

{#if auth.enabled}
	{#if auth.user}
		<div class="flex items-center gap-2">
			<a
				href="/account"
				class="hidden rounded-md px-2 py-1.5 text-small text-muted hover:bg-surface-2 hover:no-underline sm:inline"
				>{auth.user.email}</a
			>
			<button
				class="rounded-md px-2.5 py-1.5 text-small text-muted hover:bg-surface-2"
				onclick={() => auth.signOut()}>Sign out</button
			>
		</div>
	{:else}
		<button
			class="rounded-md px-2.5 py-1.5 text-small text-muted hover:bg-surface-2"
			onclick={() => {
				open = true;
				mode = 'in';
			}}>Sign in</button
		>
	{/if}

	{#if open && !auth.user}
		<div
			class="acct-overlay"
			role="dialog"
			aria-modal="true"
			aria-label={mode === 'in' ? 'Sign in' : 'Create account'}
		>
			<div class="acct-card">
				<h2 class="mb-1 text-h3">{mode === 'in' ? 'Sign in' : 'Create account'}</h2>
				<p class="mb-4 text-small text-muted">
					Sync your reading preferences across devices.
				</p>
				<form onsubmit={submit} class="space-y-3">
					<input
						bind:value={email}
						type="email"
						required
						placeholder="Email"
						autocomplete="email"
						class="w-full rounded-sm border border-border bg-bg px-3 py-2 text-body text-text"
					/>
					<input
						bind:value={password}
						type="password"
						required
						minlength="6"
						placeholder="Password"
						autocomplete={mode === 'in' ? 'current-password' : 'new-password'}
						class="w-full rounded-sm border border-border bg-bg px-3 py-2 text-body text-text"
					/>
					{#if error}<p class="text-small text-danger">{error}</p>{/if}
					{#if notice}<p class="text-small text-accent">{notice}</p>{/if}
					<button class="btn btn-primary w-full" type="submit" disabled={busy}>
						{busy ? '…' : mode === 'in' ? 'Sign in' : 'Create account'}
					</button>
				</form>
				<div class="mt-3 flex items-center justify-between text-small">
					<button
						class="text-accent"
						onclick={() => {
							mode = mode === 'in' ? 'up' : 'in';
							error = null;
							notice = null;
						}}
					>
						{mode === 'in' ? 'Create an account' : 'Have an account? Sign in'}
					</button>
					<button class="text-muted hover:text-text" onclick={() => (open = false)}>Close</button>
				</div>
			</div>
		</div>
	{/if}
{/if}

<style>
	.acct-overlay {
		position: fixed;
		inset: 0;
		z-index: 50;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
		background: rgb(0 0 0 / 0.4);
	}
	.acct-card {
		width: 100%;
		max-width: 24rem;
		border-radius: var(--radius-card);
		border: 1px solid var(--border);
		background: var(--surface);
		padding: 1.5rem;
		box-shadow: 0 10px 40px rgb(0 0 0 / 0.35);
	}
</style>
