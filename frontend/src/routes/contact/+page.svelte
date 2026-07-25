<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;
</script>

<svelte:head><title>{t('nav.contact')} — Ochorus</title></svelte:head>

<div class="mx-auto max-w-2xl px-5 py-12">
	<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">{t('nav.contact')}</p>
	<h1 class="text-display mb-6">{t('contact.heading')}</h1>

	<p class="text-body text-muted">
		{t('contact.intro')}
	</p>

	<div class="mt-8 rounded-card border border-border bg-surface-2 p-6">
		<h2 class="text-h3 mb-1">{t('contact.title')}</h2>
		<p class="text-small text-muted">
			{t('contact.messageSub')}
		</p>
	</div>

	<p class="mt-8 text-small text-muted">{t('contact.basedIn')}</p>
</div>
