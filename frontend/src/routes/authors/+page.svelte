<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { i18n } from '$lib/i18n.svelte';

	// There is no standalone /authors listing — the author directory lives at
	// /biographies. This page exists only as a prerender anchor (per-locale author
	// detail pages are enumerated by authors/[slug]'s own entries generator, not
	// by crawling this page). Keep it out of the index so it isn't a thin,
	// contentless duplicate of the real listing, and bounce anyone who lands here.
	// prerender refresh: sw/lg long author biographies (#354)
	const t = i18n.t;
	onMount(() => goto(localizeHref('/biographies'), { replaceState: true }));
</script>

<svelte:head>
	<meta name="robots" content="noindex,follow" />
</svelte:head>

<p class="mx-auto max-w-xl px-5 py-24 text-center text-body text-muted">
	<a href={localizeHref('/biographies')}>{t('nav.biographies')}</a>
</p>
