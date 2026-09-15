<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { loginHref as buildLoginHref } from '$lib/loginHref';
	import { fetchAdminManualUrl } from '$lib/library-admin';

	const t = i18n.t;

	// The Admin Manual PDF (super admins only). The endpoint is bearer-gated, so we
	// fetch the blob and open it in a new tab — opened synchronously on the click so
	// the popup isn't blocked, then pointed at the PDF once it downloads.
	let manualLoading = $state(false);
	async function openManual() {
		if (manualLoading) return;
		const tab = window.open('', '_blank');
		manualLoading = true;
		try {
			const url = await fetchAdminManualUrl();
			if (tab) tab.location.href = url;
			else window.location.href = url; // popup blocked — fall back to this tab
		} catch {
			tab?.close();
		} finally {
			manualLoading = false;
			open = false;
		}
	}

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
					{#if auth.hasAdminAccess}
						<a class="account-item" href={localizeHref('/admin')} onclick={() => (open = false)}
							>Admin</a
						>
					{/if}
					{#if auth.isAdmin}
						<!-- Super admins only (auth.isAdmin is the super-admin flag). The
						     manual PDF is bearer-gated, so this fetches it and opens the blob. -->
						<button class="account-item" onclick={openManual} disabled={manualLoading}>
							{manualLoading ? 'Opening…' : 'Admin Manual PDF'}
						</button>
					{/if}
					<a class="account-item" href={localizeHref('/favorites')} onclick={() => (open = false)}
						>{t('fav.yourFavorites')}</a
					>
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
