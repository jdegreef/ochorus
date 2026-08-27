<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { loginHref as buildLoginHref } from '$lib/loginHref';

	const t = i18n.t;

	// Matches Take Root's account control: a round initials avatar that opens a
	// small dropdown (email + account + sign out); a soft button when signed out.
	let open = $state(false);
	let root = $state<HTMLDivElement>();

	const initials = $derived(
		((auth.displayName || auth.user?.email)?.[0] ?? '?').toUpperCase()
	);

	// Preserve where the user was, so sign-in returns them there. The locale
	// handling is subtle enough to be worth testing — see $lib/loginHref.
	const loginHref = $derived(buildLoginHref($page.url.pathname, $page.url.search));

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
				aria-expanded={open}
				aria-controls={open ? 'account-menu' : undefined}
				aria-label={t('account.title')}
				onclick={(e) => {
					e.stopPropagation();
					open = !open;
				}}
			>
				{initials}
			</button>
			{#if open}
				<!-- A labelled group of links, not a menu: role="menu" promises
				     arrow-key navigation between menuitem children, and this has
				     neither. Same treatment QuickSettings uses next to it in the bar.
				     aria-controls only while the panel exists — an IDREF pointing at
				     nothing is worse than none. -->
				<div id="account-menu" class="account-menu" role="group" aria-label={t('account.title')}>
					<div class="truncate px-3 py-1.5">
						{#if auth.displayName}
							<div class="text-small font-semibold text-text">{auth.displayName}</div>
						{/if}
						<div class="truncate text-small text-muted">{auth.user.email}</div>
					</div>
					<div class="my-1 border-t border-border"></div>
					{#if auth.isAdmin}
						<a class="account-item" href={localizeHref('/admin')} onclick={() => (open = false)}
							>Admin</a
						>
					{/if}
					<a class="account-item" href={localizeHref('/notebook')} onclick={() => (open = false)}
						>{t('notebook.title')}</a
					>
					<a class="account-item" href={localizeHref('/settings')} onclick={() => (open = false)}
						>{t('settings.title')}</a
					>
					<button
						class="account-item"
						onclick={() => {
							open = false;
							auth.signOut();
						}}>{t('account.signOut')}</button
					>
				</div>
			{/if}
		</div>
	{:else}
		<a href={localizeHref(loginHref)} class="btn btn-sm btn-primary hover:no-underline">
			{t('account.signIn')}
		</a>
	{/if}
{/if}
