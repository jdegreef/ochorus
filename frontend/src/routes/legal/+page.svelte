<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';

	const t = i18n.t;
</script>

<svelte:head><title>{t('legal.title')} — Ochorus</title></svelte:head>

<div class="mx-auto max-w-2xl px-5 py-12">
	<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">Ochorus</p>
	<h1 class="text-display mb-6">{t('legal.title')}</h1>

	<div class="reading-page space-y-5 text-body text-muted">
		<p>{t('legal.intro')}</p>

		<h2 class="text-h2 !text-text pt-2">{t('legal.privacyHeading')}</h2>
		<p>{t('legal.privacyP1')}</p>
		<p>{t('legal.privacyP2')}</p>
		<p>{t('legal.privacyP3')}</p>
		<p>{t('legal.privacyP4')}</p>
		<p>{t('legal.privacyP5')}</p>

		<h2 class="text-h2 !text-text pt-2">{t('legal.termsHeading')}</h2>
		<p>{t('legal.termsP1')}</p>
		<p>{t('legal.termsP2')}</p>
		<p>{t('legal.termsP3')}</p>
		<p>{t('legal.termsP4')}</p>
		<p>{t('legal.termsP5')}</p>

		<p class="pt-2 text-small">{t('legal.ministry')}</p>
		<p class="text-small">{t('legal.updated')}</p>
	</div>

	<div class="mt-10">
		<a href={localizeHref('/about')} class="btn btn-ghost">{t('nav.about')}</a>
	</div>
</div>
