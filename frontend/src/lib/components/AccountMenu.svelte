<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$lib/auth.svelte';

	// Preserve where the user was, so sign-in returns them there.
	const loginHref = $derived(
		$page.url.pathname.startsWith('/login')
			? '/login'
			: `/login?redirect=${encodeURIComponent($page.url.pathname)}`
	);
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
		<a
			href={loginHref}
			class="rounded-md px-2.5 py-1.5 text-small text-muted hover:bg-surface-2 hover:no-underline"
		>
			Sign in
		</a>
	{/if}
{/if}
