<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import DrawerShell from '$lib/components/DrawerShell.svelte';
	import SignUpForm from '$lib/components/SignUpForm.svelte';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { loginHref } from '$lib/loginHref';
	import { withSource } from '$lib/signupSource';
	import { signInSheet } from '$lib/signInSheet.svelte';

	/**
	 * Create an account without leaving the page: Google, or an email and a
	 * password (SignUpForm). A bottom sheet on phones. It closes itself once a
	 * session exists — the auth listener has already merged this device's
	 * reading into the account by then. "Sign in" goes to the full /login, which
	 * comes back here afterwards.
	 */
	const t = i18n.t;
	let email = $state('');

	$effect(() => {
		if (auth.user && signInSheet.open) signInSheet.close();
	});

	function signIn() {
		const href = loginHref($page.url.pathname, $page.url.search);
		signInSheet.close();
		goto(localizeHref(signInSheet.source ? withSource(href, signInSheet.source) : href));
	}
</script>

<DrawerShell bind:open={signInSheet.open} title={t('login.sheetTitle')} placement="bottom">
	<div class="sheet-body">
		<p class="text-small text-muted">{t('login.sheetStay')}</p>
		{#if signInSheet.open}
			<SignUpForm bind:email returnTo={$page.url.href} onSignIn={signIn} />
		{/if}
	</div>
</DrawerShell>

<style>
	.sheet-body {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		max-width: 26rem;
		margin-inline: auto;
		width: 100%;
	}
</style>
