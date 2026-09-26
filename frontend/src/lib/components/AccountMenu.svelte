<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { loginHref as buildLoginHref } from '$lib/loginHref';
	import { fetchAdminManualUrl, fetchLanguageAdminManualUrl } from '$lib/library-admin';
	import FeedbackDialog from '$lib/components/FeedbackDialog.svelte';
	import { dismissable } from '$lib/actions/dismissable';

	const t = i18n.t;

	// The feedback modal is opened from this menu; the menu closes as it opens.
	let feedbackOpen = $state(false);

	// The operator manual PDFs (super admins see the whole-console one; language
	// admins see their own). The endpoints are bearer-gated, so we fetch the blob
	// and open it in a new tab — opened synchronously on the click so the popup
	// isn't blocked, then pointed at the PDF once it downloads. One in flight at a
	// time (`manualLoading`), so the two buttons can't overlap.
	let manualLoading = $state(false);
	async function openManual(fetchUrl: () => Promise<string>) {
		if (manualLoading) return;
		const tab = window.open('', '_blank');
		manualLoading = true;
		try {
			const url = await fetchUrl();
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

	const initials = $derived(
		((auth.displayName || auth.user?.email)?.[0] ?? '?').toUpperCase()
	);

	// Preserve where the user was, so sign-in returns them there. The locale
	// handling is subtle enough to be worth testing — see $lib/loginHref.
	const loginHref = $derived(buildLoginHref($page.url.pathname, $page.url.search));
</script>

{#if auth.enabled}
	{#if auth.user}
		<div class="account" use:dismissable={{ open, onDismiss: () => (open = false) }}>
			<button
				class="account-btn"
				aria-expanded={open}
				aria-controls={open ? 'account-menu' : undefined}
				aria-label={t('account.title')}
				onclick={() => (open = !open)}
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
						<!-- A language admin (any non-super admin) sees "Language Admin";
						     the super admin keeps "Admin". Same /admin destination. -->
						<a class="account-item" href={localizeHref('/admin')} onclick={() => (open = false)}
							>{auth.adminLabel}</a
						>
					{/if}
					{#if auth.isAdmin}
						<!-- Super admins only (auth.isAdmin is the super-admin flag). The
						     manual PDF is bearer-gated, so this fetches it and opens the blob. -->
						<button class="account-item" onclick={() => openManual(fetchAdminManualUrl)} disabled={manualLoading}>
							{manualLoading ? 'Opening…' : 'Admin Manual PDF'}
						</button>
					{:else if auth.isLanguageAdmin && auth.can('reporting')}
						<!-- The language-admin handbook, sitting right under their access
						     entry — the twin of the super admin's manual button above. Gated
						     on `reporting` to match the endpoint (REPORTING/view), so the
						     button never shows to a grantee whose fetch would 403. Every role
						     preset holds reporting, so real language admins always see it. -->
						<button class="account-item" onclick={() => openManual(fetchLanguageAdminManualUrl)} disabled={manualLoading}>
							{manualLoading ? 'Opening…' : 'Language Admin Manual PDF'}
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
							feedbackOpen = true;
						}}>{t('feedback.send')}</button
					>
					<button
						class="account-item"
						disabled={auth.signingOut}
						onclick={async () => {
							await auth.signOut();
							open = false;
						}}>{auth.signingOut ? t('settings.syncing') : t('account.signOut')}</button
					>
				</div>
			{/if}
			{#if feedbackOpen}
				<FeedbackDialog onClose={() => (feedbackOpen = false)} />
			{/if}
		</div>
	{:else}
		<a href={localizeHref(loginHref)} class="btn btn-sm btn-primary hover:no-underline">
			{t('account.signIn')}
		</a>
	{/if}
{/if}
