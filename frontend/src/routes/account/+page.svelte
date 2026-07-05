<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import ContinueReading from '$lib/components/ContinueReading.svelte';

	let { data } = $props();
	const t = i18n.t;
</script>

<svelte:head><title>{t('account.title')} — Ochorus</title></svelte:head>

<div class="mx-auto max-w-5xl px-5 py-10">
	<h1 class="text-h1 mb-2 px-0">{t('account.title')}</h1>

	{#if auth.user}
		<p class="text-body text-muted">
			{t('account.signedInAs')} <span class="font-semibold text-text">{auth.user.email}</span> ·
			{t('account.syncNote')}
		</p>
		<button class="btn btn-ghost mt-4" onclick={() => auth.signOut()}>{t('account.signOut')}</button>
	{:else if auth.enabled}
		<p class="text-body text-muted">{t('account.signedOutNote')}</p>
	{:else}
		<p class="text-body text-muted">{t('account.localNote')}</p>
	{/if}
</div>

<!-- Full in-progress list (uses local cache, which sign-in keeps synced) -->
<div class="pb-14 [&>section]:pt-4">
	<ContinueReading books={data.books} limit={24} />
</div>
