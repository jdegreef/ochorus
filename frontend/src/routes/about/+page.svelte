<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';

	const t = i18n.t;
</script>

<svelte:head><title>{t('nav.about')} — Ochorus</title></svelte:head>

<div class="mx-auto max-w-2xl px-5 py-12">
	<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">{t('nav.about')}</p>
	<h1 class="text-display mb-8">{t('about.title')}</h1>

	<div class="reading-page space-y-5 text-body text-muted">
		<h2 class="text-h2 !text-text">{t('about.heading')}</h2>
		<p>{t('about.p1')}</p>
		<p>{t('about.p2')}</p>
		<p>{t('about.p3')}</p>
		<p>{t('about.p4')}</p>
	</div>

	<div class="mt-10 flex flex-wrap gap-3">
		<a href={localizeHref('/books')} class="btn btn-primary">{t('home.browseLibrary')}</a>
		<a href={localizeHref('/contact')} class="btn btn-ghost">{t('about.getInTouch')}</a>
	</div>
</div>
