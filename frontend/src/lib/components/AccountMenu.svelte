<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$lib/auth.svelte';

	// Matches Take Root's account control: a round initials avatar that opens a
	// small dropdown (email + account + sign out); a soft button when signed out.
	let open = $state(false);
	let root = $state<HTMLDivElement>();

	const initials = $derived((auth.user?.email?.[0] ?? '?').toUpperCase());

	// Preserve where the user was, so sign-in returns them there.
	const loginHref = $derived(
		$page.url.pathname.startsWith('/login')
			? '/login'
			: `/login?redirect=${encodeURIComponent($page.url.pathname)}`
	);

	function onWindowClick(e: MouseEvent) {
		if (open && root && !root.contains(e.target as Node)) open = false;
	}
</script>

<svelte:window
	onclick={onWindowClick}
	onkeydown={(e) => {
		if (e.key === 'Escape') open = false;
	}}
/>

{#if auth.enabled}
	{#if auth.user}
		<div class="account" bind:this={root}>
			<button
				class="account-btn"
				aria-haspopup="menu"
				aria-expanded={open}
				aria-label="Account"
				onclick={(e) => {
					e.stopPropagation();
					open = !open;
				}}
			>
				{initials}
			</button>
			{#if open}
				<div class="account-menu" role="menu">
					<div class="truncate px-3 py-1.5 text-small text-muted">{auth.user.email}</div>
					<div class="my-1 border-t border-border"></div>
					<a class="account-item" role="menuitem" href="/account" onclick={() => (open = false)}
						>Account</a
					>
					<button
						class="account-item"
						role="menuitem"
						onclick={() => {
							open = false;
							auth.signOut();
						}}>Sign out</button
					>
				</div>
			{/if}
		</div>
	{:else}
		<a href={loginHref} class="btn btn-primary !px-3.5 !py-1.5 !text-small hover:no-underline">
			Sign in
		</a>
	{/if}
{/if}
