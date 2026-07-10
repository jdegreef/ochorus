<script lang="ts">
	import { page } from '$app/stores';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';

	const t = i18n.t;

	const status = $derived($page.status);
	const isNotFound = $derived(status === 404);
	const title = $derived(isNotFound ? t('error.notFoundTitle') : t('error.genericTitle'));
	const message = $derived(isNotFound ? t('error.notFoundMessage') : t('error.genericMessage'));
</script>

<svelte:head><title>{title} — Ochorus</title></svelte:head>

<div class="mx-auto flex max-w-md flex-col items-center px-5 py-24 text-center">
	<p class="text-display mb-1 text-muted">{status || 500}</p>
	<h1 class="text-h1 mb-3">{title}</h1>
	<p class="mb-7 text-body text-muted">{message}</p>
	<div class="flex flex-wrap items-center justify-center gap-3">
		{#if !isNotFound}
			<button class="btn btn-primary" onclick={() => location.reload()}>{t('error.tryAgain')}</button>
		{/if}
		<a class="btn btn-ghost" href={localizeHref('/')}>{t('error.goToLibrary')}</a>
	</div>
</div>
