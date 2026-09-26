<script lang="ts">
	import { page } from '$app/stores';
	import DrawerShell from '$lib/components/DrawerShell.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { auth } from '$lib/auth.svelte';
	import { lang, localeName } from '$lib/lang.svelte';
	import { loginHref, withSignup } from '$lib/loginHref';
	import { PRIMARY_NAV, ENGLISH_HUBS, ORIGINALS_DEST } from '$lib/contentNav';
	import { ACCOUNT_NAV } from '$lib/accountNav';

	/**
	 * The phone tab bar's "More": what the top nav's hamburger, gear and sign-in
	 * button hold on wider screens, in one bottom sheet. Every list comes from
	 * the source the footer uses, so the two can't drift. (A signed-in reader's
	 * avatar menu — sign out, admin, feedback — stays in the top bar.)
	 */
	let { open = $bindable(false) }: { open?: boolean } = $props();
	const t = i18n.t;

	const signIn = $derived(localizeHref(loginHref($page.url.pathname, $page.url.search)));

	/** Every link in the sheet navigates, so any link tap closes it — one
	 *  handler rather than one per link that a new row could forget. */
	function closeOnLink(e: MouseEvent) {
		if ((e.target as Element).closest('a')) open = false;
	}
</script>

<DrawerShell bind:open title={t('nav.more')} placement="bottom">
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
	<div class="more-body" onclick={closeOnLink}>
		{#if auth.enabled && !auth.user}
			<!-- The site's account-band copy (see AccountCta), plus sign-in: the
			     top bar's Sign in button is hidden where this sheet exists. -->
			<div class="more-card">
				<p class="text-h3 text-text">{t('home.signupTitle')}</p>
				<p class="mt-1 text-small text-muted">{t('login.syncNote')}</p>
				<div class="mt-3 grid grid-cols-2 gap-2">
					<a href={signIn} class="btn btn-primary">{t('account.signIn')}</a>
					<a href={withSignup(signIn)} class="btn btn-ghost">{t('login.createAccountBtn')}</a>
				</div>
			</div>
		{/if}

		<h3 class="more-heading">{t('footer.explore')}</h3>
		<div class="grid grid-cols-2 gap-2">
			{#each PRIMARY_NAV as d (d.href)}
				<a href={localizeHref(d.href)} class="more-tile"><Icon name={d.icon} size={20} />{t(d.labelKey)}</a>
			{/each}
			<a href={localizeHref(ORIGINALS_DEST.href)} class="more-tile"
				><Icon name="sparkle" size={20} />{t(ORIGINALS_DEST.labelKey)}</a
			>
		</div>
		<!-- English-only hubs, unlocalized — the footer's Discover rule. -->
		{#if lang.current === 'en'}
			<div class="mt-2 grid grid-cols-3 gap-2">
				{#each ENGLISH_HUBS as d (d.href)}
					<a href="{d.href}/" class="more-tile justify-center">{t(d.labelKey)}</a>
				{/each}
			</div>
		{/if}

		<h3 class="more-heading">{t('account.title')}</h3>
		<!-- Straight to each page, signed in or out — they all work signed out
		     (device-local first), and the tab bar's Bookshelf goes straight there
		     too. The footer's login detour is its sign-up funnel, not a gate. -->
		{#each ACCOUNT_NAV as d (d.path)}
			<a href={localizeHref(d.path)} class="more-row"
				><Icon name={d.icon} size={20} /><span>{t(d.labelKey)}</span></a
			>
		{/each}
		<!-- The Language picker lives in Settings → Reading. -->
		<a href="{localizeHref('/settings')}?section=reading" class="more-row"
			><Icon name="compass" size={20} /><span>{t('nav.language')}</span><span class="more-value"
				>{localeName(lang.current)}</span
			></a
		>

		<div class="mt-3 flex gap-5">
			<a href={localizeHref('/about')} class="more-link">{t('nav.about')}</a>
			<a href={localizeHref('/contact')} class="more-link">{t('nav.contact')}</a>
		</div>
	</div>
</DrawerShell>

<style>
	.more-body {
		overflow-y: auto;
		overscroll-behavior: contain;
		padding: 1rem 1.25rem calc(1.5rem + env(safe-area-inset-bottom));
	}
	.more-card {
		margin-bottom: 0.5rem;
		padding: 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface-2);
	}
	.more-heading {
		margin: 1.25rem 0 0.5rem;
		font-size: var(--fs-small);
		font-weight: 600;
		color: var(--muted);
	}
	.more-tile {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		min-height: 3rem;
		padding-inline: 0.8rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		font-size: var(--fs-body);
		color: var(--text);
		text-decoration: none;
	}
	.more-tile :global(svg) {
		color: var(--accent);
		flex-shrink: 0;
	}
	.more-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		min-height: 3rem;
		border-bottom: 1px solid var(--border);
		font-size: var(--fs-body);
		color: var(--text);
		text-decoration: none;
	}
	.more-row :global(svg) {
		color: var(--muted);
	}
	.more-value {
		margin-inline-start: auto;
		color: var(--muted);
	}
	.more-link {
		min-height: 2.75rem;
		display: inline-flex;
		align-items: center;
		font-size: var(--fs-small);
		color: var(--muted);
	}
	.more-tile:hover,
	.more-row:hover {
		text-decoration: none;
		background: var(--surface-2);
	}
</style>
